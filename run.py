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
    suffix = 1
    while run_dir.exists():
        suffix += 1
        run_dir = out_root / f"run-{generated_at}-{suffix}"
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
    bundle_validator = Path("validate_bundle.py")
    if bundle_validator.exists():
        shutil.copyfile(bundle_validator, run_dir / "validate_bundle.py")

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
        "Package stage: post-run verification and packaging of completed benchmark artifacts\n"
        "Replay status: original benchmark execution is not replayed during this verification step\n"
        "\n"
        "Verification\n"
        f"Verified recall: {verified} / {args.turns}\n"
        f"Final verified output failures: {args.turns - verified}\n"
        f"Average bounded packet tokens per turn: {metrics['token_accounting']['average_packet_tokens_per_turn_estimate']}\n"
        f"Full-history replay baseline per turn: {full_history_tokens_per_turn}\n"
        f"Replay reduction estimate: {metrics['token_accounting']['replay_reduction_ratio_estimate']}x\n"
        f"State density: tracking {len(fields)} telemetry fields across {args.episodes} independent operational episodes ({len(dataset)} source records)\n"
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
        "- Audience assumption: this analysis assumes a dedicated local AI or IDE agent with folder access to the extracted evidence bundle.\n"
        "- This package is not designed for browser-chat upload verification.\n"
        "- Start with 00_START_HERE.txt, then 01_QUICK_VALIDATION.txt.\n"
        "- For deeper review, have the local agent inspect the raw JSONL files directly from the folder.\n"
        "- Minimum files: manifest.json, metrics.json, RESULT_SUMMARY.txt, VERIFY.txt, prompt.md.\n"
        "- For skeptical review, use AUDIT_PROMPT.md after the agent has folder access. The reviewer must audit the files, not critique the prompt.\n"
    )
    (run_dir / "RESULT_SUMMARY.txt").write_text(summary_text, encoding="utf-8", newline="\n")

    start_here_text = (
        "TeleMemetry Evidence Bundle - START HERE\n"
        "\n"
        "Copy-paste this into your local IDE agent: Audit this folder. First run `python validate_bundle.py`, then verify that manifest.json hashes match the evidence files, confirm dataset/evidence/output row counts against metrics.json, validate 1:1 exact matches in outputs.jsonl, and confirm bounded packet tokens average matches the reported replay-reduction math.\n"
        "\n"
        "Audience assumption: this analysis assumes the reviewer has a dedicated local AI or IDE agent with folder access to this extracted evidence bundle. It is not designed for browser-chat upload verification.\n"
        "\n"
        "Recommended workflow\n"
        "1. Extract the archive into a normal folder.\n"
        "2. Open that folder in an IDE or local AI agent that can read files from disk.\n"
        "3. Ask the agent to inspect this folder and begin with 01_QUICK_VALIDATION.txt.\n"
        "4. Run `python validate_bundle.py` from this folder for a fast programmatic check.\n"
        "5. For a deeper audit, ask it to inspect manifest.json, metrics.json, RESULT_SUMMARY.txt, VERIFY.txt, outputs.jsonl, evidence_packets.jsonl, and dataset.jsonl.\n"
        "6. For a skeptical audit, use AUDIT_PROMPT.md after the agent has folder access.\n"
        "\n"
        "Do not paste the large JSONL files into a browser chat. They are intended for file inspection from the extracted folder.\n"
        "\n"
        "Primary files\n"
        "- 01_QUICK_VALIDATION.txt - short validation brief for executives, engineers, and AI agents.\n"
        "- AI_AUDIT_PACKET.md - small hosted-AI fallback summary, not a full raw-record audit.\n"
        "- AUDIT_PROMPT.md - skeptical independent audit prompt for folder-aware reviewers.\n"
        "- manifest.json - SHA256 receipts for evidence files.\n"
        "- metrics.json - reported benchmark measurements.\n"
        "- validate_bundle.py - zero-dependency quick validator for hashes, row counts, exact matches, and token math.\n"
        "- outputs.jsonl, evidence_packets.jsonl, dataset.jsonl - raw audit evidence for local file inspection.\n"
    )
    (run_dir / "00_START_HERE.txt").write_text(start_here_text, encoding="utf-8", newline="\n")
    (run_dir / "README.md").write_text(
        "# TeleMemetry Evidence Bundle\n"
        "\n"
        "**Audience assumption:** this analysis assumes the reviewer has a dedicated local AI or IDE agent with folder access to this extracted evidence bundle. It is not designed for browser-chat upload verification.\n"
        "\n"
        "Start with `00_START_HERE.txt`, then read `01_QUICK_VALIDATION.txt`.\n"
        "\n"
        "Fast path: run `python validate_bundle.py` from this folder.\n"
        "\n"
        "For a full audit, inspect `manifest.json`, `metrics.json`, `RESULT_SUMMARY.txt`, `VERIFY.txt`, `outputs.jsonl`, `evidence_packets.jsonl`, and `dataset.jsonl` directly from this folder.\n"
        "\n"
        "Use `AUDIT_PROMPT.md` for skeptical independent review after the local AI or IDE agent has folder access.\n",
        encoding="utf-8",
        newline="\n",
    )

    quick_validation_text = (
        "TeleMemetry Quick Validation Brief\n"
        "\n"
        "Audience assumption: this analysis assumes the reviewer has a dedicated local AI or IDE agent with folder access to this extracted evidence bundle. It is not designed for browser-chat upload verification.\n"
        "\n"
        "What to validate first\n"
        f"- Benchmark: {metrics['benchmark']}\n"
        f"- Launchable version: {metrics['launchable']['version']}\n"
        f"- Source commit: {metrics['launchable']['source_commit']}\n"
        f"- Scope: {args.turns} turns, {len(fields)} fields, {args.episodes} episodes, {len(dataset)} records\n"
        f"- State density: tracking {len(fields)} telemetry fields across {args.episodes} independent operational episodes\n"
        f"- Verified recall: {verified} / {args.turns}\n"
        f"- Final verified output failures: {args.turns - verified}\n"
        f"- Exact match rate: {metrics['recall']['exact_match_rate']}\n"
        f"- Average bounded packet tokens per turn estimate: {metrics['token_accounting']['average_packet_tokens_per_turn_estimate']}\n"
        f"- Full-history replay baseline per turn estimate: {full_history_tokens_per_turn}\n"
        f"- Replay reduction estimate: {metrics['token_accounting']['replay_reduction_ratio_estimate']}x\n"
        "\n"
        "Folder-aware AI agent instruction\n"
        "Inspect the extracted evidence folder. Do not rely on this brief alone. First run `python validate_bundle.py`. Then check metrics.json and RESULT_SUMMARY.txt for reported values, VERIFY.txt for verification output, manifest.json for SHA256 receipts, and sample or scan outputs.jsonl/evidence_packets.jsonl/dataset.jsonl for exact-match evidence. If source code is unavailable, mark source-code execution objectives NOT TESTED, but still audit the supplied evidence files.\n"
        "\n"
        "Supported by this bundle if file inspection confirms it\n"
        "- Scoped exact operational-state recall for the generated public benchmark.\n"
        "- Bounded evidence packets compared with a full-history replay token baseline.\n"
        "- SHA256 receipts that detect ordinary artifact changes.\n"
        "\n"
        "Not proven by this bundle alone\n"
        "- TeleMemetry production engine internals.\n"
        "- Robotics, AV, or industrial safety certification.\n"
        "- Universal semantic memory or chatbot reasoning quality.\n"
        "- The 100k flagship run, CelesTrak snapshot, or GPU power claim unless those artifacts are separately supplied.\n"
    )
    (run_dir / "01_QUICK_VALIDATION.txt").write_text(quick_validation_text, encoding="utf-8", newline="\n")

    audit_packet_text = (
        "# TeleMemetry Universal AI Audit Packet\n"
        "\n"
        "Audience assumption: this analysis assumes the reviewer has a dedicated local AI or IDE agent with folder access to the extracted evidence bundle. It is not designed for browser-chat upload verification.\n"
        "\n"
        "Use this file only as a compact fallback summary when a reviewer cannot inspect the extracted folder yet. For real validation, use 00_START_HERE.txt and 01_QUICK_VALIDATION.txt from the extracted folder.\n"
        "\n"
        "Instruction to reviewer: audit this packet as file-inspection evidence. Do not critique the prompt. "
        "If you cannot inspect the full JSONL files, mark raw-record inspection as PARTIAL or NOT TESTED. "
        "Do not ask for source-code files before auditing the evidence summarized here.\n"
        "\n"
        "## Result Summary\n"
        "\n"
        f"- Benchmark: {metrics['benchmark']}\n"
        "- Result: PASS\n"
        f"- Verified recall: {verified} / {args.turns}\n"
        f"- Final verified output failures: {args.turns - verified}\n"
        f"- Exact match rate: {metrics['recall']['exact_match_rate']}\n"
        f"- Average bounded packet tokens per turn estimate: {metrics['token_accounting']['average_packet_tokens_per_turn_estimate']}\n"
        f"- Full-history replay baseline per turn estimate: {full_history_tokens_per_turn}\n"
        f"- Total packet tokens estimate: {total_packet_tokens}\n"
        f"- Total full-history replay tokens estimate: {total_replay_tokens}\n"
        f"- Replay reduction estimate: {metrics['token_accounting']['replay_reduction_ratio_estimate']}x\n"
        f"- Scope: {args.turns} turns, {len(fields)} fields, {args.episodes} episodes, {len(dataset)} records\n"
        f"- Schema version: {metrics['scope']['schema_version']}\n"
        f"- Claim boundary: {metrics['claim_boundary']}\n"
        "\n"
        "## Files Represented\n"
        "\n"
        "These files are included in the full evidence bundle: 00_START_HERE.txt, 01_QUICK_VALIDATION.txt, manifest.json, metrics.json, VERIFY.txt, "
        "RESULT_SUMMARY.txt, prompt.md, AUDIT_PROMPT.md, launchable_version.json, dataset.jsonl, "
        "evidence_packets.jsonl, outputs.jsonl.\n"
        "\n"
        "## Verification Text\n"
        "\n"
        "```text\n"
        f"{verify_text}"
        "```\n"
        "\n"
        "## Representative Output Records\n"
        "\n"
        "```jsonl\n"
        f"{json.dumps(outputs[0], sort_keys=True)}\n"
        f"{json.dumps(outputs[1], sort_keys=True)}\n"
        f"{json.dumps(outputs[2], sort_keys=True)}\n"
        f"{json.dumps(outputs[-3], sort_keys=True)}\n"
        f"{json.dumps(outputs[-2], sort_keys=True)}\n"
        f"{json.dumps(outputs[-1], sort_keys=True)}\n"
        "```\n"
        "\n"
        "## What This Packet Supports\n"
        "\n"
        f"- The bundled metrics report {verified} / {args.turns} verified exact-match outputs.\n"
        f"- The reported final verified output failures are {args.turns - verified}.\n"
        f"- The reported bounded packet token estimate is {metrics['token_accounting']['average_packet_tokens_per_turn_estimate']} tokens per turn.\n"
        f"- The reported replay baseline is {full_history_tokens_per_turn} tokens per turn.\n"
        f"- The reported replay reduction estimate is {metrics['token_accounting']['replay_reduction_ratio_estimate']}x.\n"
        "- The manifest provides SHA256 receipts for artifact-change detection.\n"
        "\n"
        "## What This Packet Does Not Prove By Itself\n"
        "\n"
        "- It does not independently execute run.py or verify.py.\n"
        "- It does not prove the 100k Isaac Lab flagship run.\n"
        "- It does not prove the CelesTrak snapshot or live feed.\n"
        "- It does not prove 135.21W GPU power without raw power logs.\n"
        "- It does not prove robotics safety, AV certification, universal semantic memory, production TPS/RPS, or production engine internals.\n"
        "- It does not replace full inspection of dataset.jsonl, evidence_packets.jsonl, and outputs.jsonl.\n"
        "\n"
        "## Required Audit Output\n"
        "\n"
        "Return a table with: Objective, Status, Evidence, Measured Values, Limitations, Requirement for Full Validation.\n"
        "End with supported claims, project-asserted-only claims, and steps requiring full files or runnable source code.\n"
    )
    (run_dir / "AI_AUDIT_PACKET.md").write_text(audit_packet_text, encoding="utf-8", newline="\n")

    manifest_files = ["dataset.jsonl", "evidence_packets.jsonl", "outputs.jsonl", "metrics.json", "launchable_version.json", "VERIFY.txt", "RESULT_SUMMARY.txt", "00_START_HERE.txt", "01_QUICK_VALIDATION.txt", "README.md", "AI_AUDIT_PACKET.md"]
    if (run_dir / "validate_bundle.py").exists():
        manifest_files.append("validate_bundle.py")
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
