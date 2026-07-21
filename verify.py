#!/usr/bin/env python3
"""Verify a TeleMemetry public reproduction result package."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

REQUIRED_MANIFEST_FILES = {
    "dataset.jsonl",
    "evidence_packets.jsonl",
    "outputs.jsonl",
    "metrics.json",
    "VERIFY.txt",
    "RESULT_SUMMARY.txt",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a public TeleMemetry result package.")
    parser.add_argument("run_dir", help="Result directory, for example results/latest")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    manifest_path = run_dir / "manifest.json"
    metrics_path = run_dir / "metrics.json"
    dataset_path = run_dir / "dataset.jsonl"
    evidence_path = run_dir / "evidence_packets.jsonl"
    outputs_path = run_dir / "outputs.jsonl"

    require(manifest_path.exists(), f"missing manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_paths = {entry["path"] for entry in manifest["files"]}
    missing_required = sorted(REQUIRED_MANIFEST_FILES - manifest_paths)
    require(not missing_required, f"manifest missing required artifacts: {', '.join(missing_required)}")

    for entry in manifest["files"]:
        path = run_dir / entry["path"]
        require(path.exists(), f"missing artifact: {entry['path']}")
        actual = file_sha256(path)
        require(actual == entry["sha256"], f"sha256 mismatch for {entry['path']}: {actual} != {entry['sha256']}")

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    version_path = run_dir / "launchable_version.json"
    if version_path.exists():
        launchable_version = json.loads(version_path.read_text(encoding="utf-8"))
        require(launchable_version == metrics.get("launchable"), "launchable_version.json does not match metrics.json")

    dataset = load_jsonl(dataset_path)
    evidence_packets = load_jsonl(evidence_path)
    outputs = load_jsonl(outputs_path)

    scope = metrics["scope"]
    total_turns = metrics["recall"]["total_turns"]
    require(len(outputs) == total_turns, f"outputs row count mismatch: {len(outputs)} != {total_turns}")
    require(len(evidence_packets) == total_turns, f"evidence packet row count mismatch: {len(evidence_packets)} != {total_turns}")
    require(len(dataset) == scope["records"], f"dataset record count mismatch: {len(dataset)} != {scope['records']}")

    lookup = {}
    for record in dataset:
        record_without_hash = dict(record)
        record_hash = record_without_hash.pop("record_sha256", None)
        expected_hash = sha256_text(stable_json(record_without_hash))
        require(record_hash == expected_hash, f"dataset record_sha256 mismatch for episode={record.get('episode')} field={record.get('field')}")
        key = (record["episode"], record["field"])
        require(key not in lookup, f"duplicate dataset key: {key}")
        lookup[key] = record

    total_packet_tokens = 0
    exact_matches = 0
    for turn, (packet, output) in enumerate(zip(evidence_packets, outputs)):
        require(packet.get("turn") == turn, f"evidence turn sequence mismatch at row {turn}")
        require(output.get("turn") == turn, f"output turn sequence mismatch at row {turn}")
        require(packet.get("episode") == output.get("episode"), f"episode mismatch at turn {turn}")
        require(packet.get("field") == output.get("field"), f"field mismatch at turn {turn}")

        key = (packet["episode"], packet["field"])
        require(key in lookup, f"missing dataset reference for turn {turn}: {key}")
        record = lookup[key]
        require(packet.get("source_record_sha256") == record["record_sha256"], f"source_record_sha256 mismatch at turn {turn}")
        require(packet.get("value") == record["value"], f"evidence packet value mismatch at turn {turn}")
        require(output.get("expected") == record["value"], f"output expected value mismatch at turn {turn}")
        require(output.get("actual") == packet["value"], f"output actual value mismatch at turn {turn}")
        require(output.get("exact_match") is True, f"exact_match flag false at turn {turn}")
        require(output.get("expected") == output.get("actual"), f"recall verification failed at turn {turn}")

        packet_without_tokens = dict(packet)
        packet_tokens = packet_without_tokens.pop("packet_tokens_estimate", None)
        expected_packet_tokens = estimate_tokens(stable_json(packet_without_tokens))
        require(packet_tokens == expected_packet_tokens, f"packet token estimate mismatch at turn {turn}: {packet_tokens} != {expected_packet_tokens}")
        total_packet_tokens += packet_tokens
        exact_matches += 1

    full_history_json = "\n".join(stable_json(row) for row in dataset)
    full_history_tokens_per_turn = estimate_tokens(full_history_json)
    total_replay_tokens = full_history_tokens_per_turn * total_turns
    replay_reduction = round(total_replay_tokens / total_packet_tokens, 2)
    average_packet_tokens = round(total_packet_tokens / total_turns, 2)

    require(exact_matches == metrics["recall"]["verified_turns"], "verified turn count does not match metrics.json")
    require(exact_matches == total_turns, f"recall verification failed: {exact_matches} / {total_turns}")
    require(metrics["recall"]["final_verified_output_failures"] == total_turns - exact_matches, "final failure count mismatch")
    require(metrics["token_accounting"]["average_packet_tokens_per_turn_estimate"] == average_packet_tokens, "average packet token estimate mismatch")
    require(metrics["token_accounting"]["full_history_replay_tokens_per_turn_estimate"] == full_history_tokens_per_turn, "full-history replay token estimate mismatch")
    require(metrics["token_accounting"]["total_packet_tokens_estimate"] == total_packet_tokens, "total packet token estimate mismatch")
    require(metrics["token_accounting"]["total_full_history_replay_tokens_estimate"] == total_replay_tokens, "total replay token estimate mismatch")
    require(metrics["token_accounting"]["replay_reduction_ratio_estimate"] == replay_reduction, "replay reduction estimate mismatch")

    print("Verification passed")
    print(f"Verified turns: {exact_matches} / {total_turns}")
    print(f"Final verified output failures: {metrics['recall']['final_verified_output_failures']}")
    print(f"Average packet tokens per turn estimate: {metrics['token_accounting']['average_packet_tokens_per_turn_estimate']}")
    print(f"Replay reduction ratio estimate: {metrics['token_accounting']['replay_reduction_ratio_estimate']}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
