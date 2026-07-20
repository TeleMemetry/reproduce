#!/usr/bin/env python3
"""Verify a TeleMemetry public reproduction result package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a public TeleMemetry result package.")
    parser.add_argument("run_dir", help="Result directory, for example results/latest")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    manifest_path = run_dir / "manifest.json"
    metrics_path = run_dir / "metrics.json"
    outputs_path = run_dir / "outputs.jsonl"

    if not manifest_path.exists():
        raise SystemExit(f"missing manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        path = run_dir / entry["path"]
        if not path.exists():
            raise SystemExit(f"missing artifact: {entry['path']}")
        actual = file_sha256(path)
        if actual != entry["sha256"]:
            raise SystemExit(f"sha256 mismatch for {entry['path']}: {actual} != {entry['sha256']}")

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    outputs = load_jsonl(outputs_path)
    exact_matches = sum(1 for row in outputs if row.get("exact_match") and row.get("expected") == row.get("actual"))
    total_turns = metrics["recall"]["total_turns"]

    if exact_matches != metrics["recall"]["verified_turns"]:
        raise SystemExit("verified turn count does not match metrics.json")
    if exact_matches != total_turns:
        raise SystemExit(f"recall verification failed: {exact_matches} / {total_turns}")

    print("Verification passed")
    print(f"Verified turns: {exact_matches} / {total_turns}")
    print(f"Final verified output failures: {metrics['recall']['final_verified_output_failures']}")
    print(f"Average packet tokens per turn estimate: {metrics['token_accounting']['average_packet_tokens_per_turn_estimate']}")
    print(f"Replay reduction ratio estimate: {metrics['token_accounting']['replay_reduction_ratio_estimate']}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
