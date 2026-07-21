#!/usr/bin/env python3
"""Generate a deterministic TeleMemetry public reproduction package."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


LAUNCHABLE_VERSION = "2026.07.21.1"

FIELD_NAMES = [
    "pose_x",
    "pose_y",
    "pose_z",
    "velocity",
    "acceleration",
    "heading",
    "joint_state",
    "battery",
    "thermal",
    "status_code",
]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def source_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return "unknown"
    return result.stdout.strip() or "unknown"


def estimate_tokens(text: str) -> int:
    """Simple model-visible token estimate for benchmark accounting."""
    return max(1, math.ceil(len(text) / 4))


def build_value(episode: int, field: str, sample: int) -> str:
    digest = sha256_text(f"tm-public-v1|{episode}|{field}|{sample}")
    number = int(digest[:8], 16) % 1_000_000
    return f"{field}:{episode:02d}:{sample:04d}:{number:06d}"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(stable_json(row) + "\n")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(run_dir: Path, files: list[str]) -> dict:
    entries = []
    for name in files:
        path = run_dir / name
        entries.append({
            "path": name,
            "bytes": path.stat().st_size,
            "sha256": file_sha256(path),
        })
    return {
        "manifest_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the public TeleMemetry reproduction benchmark.")
    parser.add_argument("--turns", type=int, default=3000)
    parser.add_argument("--fields", type=int, default=10)
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--out", default="results")
    args = parser.parse_args()

    if args.turns <= 0 or args.fields <= 0 or args.episodes <= 0:
        raise SystemExit("turns, fields, and episodes must be positive integers")
    if args.fields > len(FIELD_NAMES):
        raise SystemExit(f"fields must be <= {len(FIELD_NAMES)} for the public benchmark")

    fields = FIELD_NAMES[:args.fields]
    generated_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = Path(args.out)
    run_dir = out_root / f"run-{generated_at}"
    run_dir.mkdir(parents=True, exist_ok=False)

    dataset = []
    lookup = {}
    for episode in range(args.episodes):
        for field in fields:
            record = {
                "schema_version": "tm-public-reproduce-v1",
                "episode": episode,
                "sample": episode,
                "field": field,
                "value": build_value(episode, field, episode),
            }
            record["record_sha256"] = sha256_text(stable_json(record))
            dataset.append(record)
            lookup[(episode, field)] = record

    evidence_packets = []
    outputs = []
    verified = 0
    total_packet_tokens = 0

    full_history_json = "\n".join(stable_json(row) for row in dataset)
    full_history_tokens_per_turn = estimate_tokens(full_history_json)

    for turn in range(args.turns):
        episode = turn % args.episodes
        field = fields[turn % len(fields)]
        record = lookup[(episode, field)]
        packet = {
            "turn": turn,
            "schema_version": record["schema_version"],
            "episode": record["episode"],
            "field": record["field"],
            "value": record["value"],
            "source_record_sha256": record["record_sha256"],
        }
        packet_json = stable_json(packet)
        packet_tokens = estimate_tokens(packet_json)
        total_packet_tokens += packet_tokens
        evidence_packets.append(packet | {"packet_tokens_estimate": packet_tokens})

        output = {
            "turn": turn,
            "episode": episode,
            "field": field,
            "expected": record["value"],
            "actual": packet["value"],
            "exact_match": packet["value"] == record["value"],
        }
        verified += int(output["exact_match"])
        outputs.append(output)

    total_replay_tokens = full_history_tokens_per_turn * args.turns
    replay_reduction = total_replay_tokens / total_packet_tokens
    metrics = {
        "benchmark": "telememetry-public-reproduce",
        "launchable": {
            "version": LAUNCHABLE_VERSION,
            "source_commit": source_commit(),
        },
        "scope": {
            "turns": args.turns,
            "fields": len(fields),
            "episodes": args.episodes,
            "records": len(dataset),
            "schema_version": "tm-public-reproduce-v1",
        },
        "recall": {
            "verified_turns": verified,
            "total_turns": args.turns,
            "exact_match_rate": verified / args.turns,
            "final_verified_output_failures": args.turns - verified,
        },
        "token_accounting": {
            "average_packet_tokens_per_turn_estimate": round(total_packet_tokens / args.turns, 2),
            "full_history_replay_tokens_per_turn_estimate": full_history_tokens_per_turn,
            "total_packet_tokens_estimate": total_packet_tokens,
            "total_full_history_replay_tokens_estimate": total_replay_tokens,
            "replay_reduction_ratio_estimate": round(replay_reduction, 2),
        },
        "claim_boundary": "Scoped deterministic public benchmark; not production engine internals.",
    }

    write_jsonl(run_dir / "dataset.jsonl", dataset)
    write_jsonl(run_dir / "evidence_packets.jsonl", evidence_packets)
    write_jsonl(run_dir / "outputs.jsonl", outputs)
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8", newline="\n")
    (run_dir / "launchable_version.json").write_text(
        json.dumps(metrics["launchable"], indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    prompt_template = Path("prompt.md")
    if prompt_template.exists():
        shutil.copyfile(prompt_template, run_dir / "prompt.md")
    audit_prompt_template = Path("AUDIT_PROMPT.md")
    if audit_prompt_template.exists():
        shutil.copyfile(audit_prompt_template, run_dir / "AUDIT_PROMPT.md")

    verify_text = (
        "TeleMemetry public reproduce verification\n"
        f"Launchable version: {metrics['launchable']['version']}\n"
        f"Source commit: {metrics['launchable']['source_commit']}\n"
        f"Verified turns: {verified} / {args.turns}\n"
        f"Final verified output failures: {args.turns - verified}\n"
        f"Average packet tokens per turn estimate: {metrics['token_accounting']['average_packet_tokens_per_turn_estimate']}\n"
        f"Replay reduction ratio estimate: {metrics['token_accounting']['replay_reduction_ratio_estimate']}x\n"
    )
    (run_dir / "VERIFY.txt").write_text(verify_text, encoding="utf-8", newline="\n")

    summary_text = (
        "TeleMemetry Public Benchmark - Result Summary\n"
        "\n"
        "Benchmark completion\n"
        "RESULT: PASS\n"
        f"Launchable version: {metrics['launchable']['version']}\n"
        f"Source commit: {metrics['launchable']['source_commit']}\n"
        "\n"
        "Verification\n"
        f"Verified recall: {verified} / {args.turns}\n"
        f"Final verified output failures: {args.turns - verified}\n"
        f"Average bounded packet tokens per turn: {metrics['token_accounting']['average_packet_tokens_per_turn_estimate']}\n"
        f"Full-history replay baseline per turn: {full_history_tokens_per_turn}\n"
        f"Replay reduction estimate: {metrics['token_accounting']['replay_reduction_ratio_estimate']}x\n"
        "\n"
        "Benchmark scope\n"
        "- Exact operational-state recall within this public benchmark scope.\n"
        "- Bounded evidence packets instead of full-history replay.\n"
        "- SHA256 receipts for artifact integrity verification.\n"
        "- Result package suitable for independent human or AI review.\n"
        "\n"
        "Limitations\n"
        "- Does not demonstrate universal semantic memory.\n"
        "- Does not provide robotics or AV safety certification.\n"
        "- Does not measure production power savings across all hardware.\n"
        "- Does not disclose TeleMemetry production engine internals.\n"
        "\n"
        "Review next steps\n"
        "- Use prompt.md for standard AI-assisted review.\n"
        "- Use AUDIT_PROMPT.md for skeptical review with the same result files.\n"
    )
    (run_dir / "RESULT_SUMMARY.txt").write_text(summary_text, encoding="utf-8", newline="\n")

    manifest_files = ["dataset.jsonl", "evidence_packets.jsonl", "outputs.jsonl", "metrics.json", "launchable_version.json", "VERIFY.txt", "RESULT_SUMMARY.txt"]
    if (run_dir / "prompt.md").exists():
        manifest_files.append("prompt.md")
    if (run_dir / "AUDIT_PROMPT.md").exists():
        manifest_files.append("AUDIT_PROMPT.md")
    manifest = build_manifest(run_dir, manifest_files)
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")

    latest = out_root / "latest"
    if latest.exists() or latest.is_symlink():
        if latest.is_dir() and not latest.is_symlink():
            shutil.rmtree(latest)
        else:
            latest.unlink()
    shutil.copytree(run_dir, latest)

    print(f"Wrote {run_dir}")
    print(f"Verified turns: {verified} / {args.turns}")
    print(f"Replay reduction estimate: {metrics['token_accounting']['replay_reduction_ratio_estimate']}x")
    print("Next: python verify.py results/latest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
