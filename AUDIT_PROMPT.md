# Independent Evidence Bundle Audit

You are not being asked to review or improve this prompt. You are being asked to audit the evidence bundle files supplied with it.

Audience assumption: this analysis assumes you have a dedicated local AI or IDE agent with folder access to the extracted TeleMemetry evidence bundle. It is not designed for browser-chat upload verification.

Before starting, inspect the evidence files in the extracted folder. The ideal workflow is to extract the evidence archive into a folder accessible by a local AI or IDE agent, then have the agent inspect that folder.

Ideal option:

- Extract the archive into an AI-agent-accessible folder and inspect the folder files directly.

Start here:

- `00_START_HERE.txt`
- `01_QUICK_VALIDATION.txt`

Minimum file set for a useful audit:

- `manifest.json`
- `metrics.json`
- `RESULT_SUMMARY.txt`
- `VERIFY.txt`
- `prompt.md`

Additional files for deeper audit:

- `dataset.jsonl`
- `evidence_packets.jsonl`
- `outputs.jsonl`

Some generated bundles may also include `launchable_version.json`; if present, inspect it and compare it to any launchable/version fields in `metrics.json`.

If neither an extracted evidence folder nor the minimum file set is accessible, stop and say: **NOT TESTED - evidence files were not provided or could not be read. Extract the evidence archive into a folder accessible by a local AI or IDE agent, then inspect 00_START_HERE.txt and 01_QUICK_VALIDATION.txt first.** Do not critique the prompt. Do not provide suggestions for improving the prompt unless explicitly asked after the audit.

If the minimum file set is accessible but the large JSONL files are not accessible, proceed with the file audit anyway. Mark raw-record inspection as `PARTIAL` or `NOT TESTED` as appropriate. If source-code files such as `run.py` or `verify.py` are not accessible, proceed with the bundle-file audit anyway. Mark only the source-code and execution objectives `NOT TESTED`. Do not ask for repository files before auditing the supplied files.

## Role

You are a skeptical technical reviewer validating claims made by the TeleMemetry evidence bundle and its published benchmark artifacts. Your job is to find where the evidence is solid and where it is not. Do not confirm the publisher's framing unless the files support it.

## Evidence Rules

- Every `PASS`, `PARTIAL`, `FAIL`, or `NOT TESTED` must cite exact evidence: file name, field name, line/sample, hash, terminal output, function name, or artifact path.
- Use `NOT TESTED` whenever you could not inspect or execute the required step.
- Do not infer behavior from README examples, site copy, or published benchmark claims.
- Distinguish **file inspection evidence** from **runtime execution evidence**.
- Report skipped steps.
- If you run commands, record OS, Python version, package versions where available, and commit/version identifiers from the bundle.
- If a benchmark cannot be executed, the result is `NOT TESTED`, not `PASS` or `FAIL`. Explain precisely what blocked execution.

## Context

TeleMemetry claims verified, exact-match operational telemetry recall, bounded active context per turn versus full-history replay, and publishes:

- A flagship Isaac Lab run: 100,000 / 100,000 verified outputs, 278 average context tokens per turn, 3,548x replay reduction, and 135.21W stress-test GPU power.
- A public reproduce / launchable default run: 3,000 turns, 10 fields, 20 episodes, expected 3,000 / 3,000 verified, about 52.96 average tokens per turn, and about 192.79x replay reduction.
- A preserved CelesTrak snapshot: 1,329 / 1,329 probes, 100% recall, dated 2026-06-01, explicitly labeled as not a currently running feed and not a sealed artifact.

Validate each objective independently. Do not assume a prior objective holds.

## Objectives

### 1. Audit the supplied result bundle

- Inspect `RESULT_SUMMARY.txt`, `VERIFY.txt`, `metrics.json`, `manifest.json`, `outputs.jsonl`, and `evidence_packets.jsonl`.
- Confirm the actual reported numbers: verified turns, final failures, average tokens per turn, replay baseline, and replay reduction.
- Report exact numbers produced. Flag any deviation, however small, and do not round in the publisher's favor.

### 2. Reproduce the default benchmark if code is available

- Do not block Objective 1 waiting for source code. This objective is separate from auditing the supplied result bundle.
- If the reproduce repo code is available, clone or run it fresh in an isolated environment with no cached state.
- Run `python run.py`, then `python verify.py results/latest` per the README or bundled instructions.
- If code execution is not possible from the supplied bundle, mark this objective `NOT TESTED` and explain what files or environment are missing.

### 3. Inspect the verification logic if code is available

- Do not block Objective 1 waiting for source code. This objective is separate from auditing the supplied result bundle.
- Read `verify.py`, `run.py`, and any exactness-comparison code if present.
- Confirm verification is exact-match against stored reference values, not fuzzy or threshold matching.
- Confirm the failure definition in code matches the docs: final output miss, missing evidence packet, or integrity failure.
- Flag any verification path that is skipped, mocked, short-circuited, or merely documented instead of executed.
- If code is not present, mark this objective `NOT TESTED`.

### 4. Validate token and replay-reduction math

- Locate where the full-history replay baseline appears in `metrics.json`, `RESULT_SUMMARY.txt`, code, or logs.
- Confirm whether it is calculated from the generated dataset and benchmark scope, or only reported as a bundled metric.
- State explicitly what the replay-reduction number includes and excludes.
- Confirm that storage, routing, hashing, packaging, and verification costs are separate system costs and not counted as model-visible context tokens.

### 5. Stress past the default scale if execution is available

- If runnable code is available, rerun with `--turns 10000 --fields 10 --episodes 20`, or higher if resources allow.
- If the public harness enforces a documented cap, report the cap and explain why the cap exists rather than treating the cap itself as a failure.
- Report whether recall stays at 100% or degrades, and at what scale failures first appear.
- Do not extrapolate a 3k result to the 100k flagship run.
- If execution is not possible, mark this objective `NOT TESTED`.

### 6. Check for scope leakage

- Confirm whether the benchmark dataset is deterministic and synthetic as claimed.
- Confirm whether the supplied result bundle shows any network calls, credentials, or external dependencies.
- If code execution is performed, flag anything that requires elevated privileges, network access, credentials, hidden services, or undisclosed dependencies.

### 7. Check SHA256 receipt integrity

- Independently recompute SHA256 hashes for result artifacts against `manifest.json`, outside any tooling the repo provides.
- Use standard OS utilities where available: `sha256sum`, `shasum -a 256`, `certutil -hashfile`, or PowerShell `Get-FileHash`.
- Confirm receipts describe final artifacts.
- State clearly that same-storage receipts detect ordinary artifact changes, but do not by themselves prove protection against simultaneous malicious replacement of both artifact and receipt.

### 8. Identify what remains unverified

Explicitly list every claim made in the site, docs, or result package that this bundle does not and cannot validate, including:

- The 100k Isaac Lab flagship run itself, unless the full artifact is attached and independently checked.
- The CelesTrak preserved snapshot or any live feed, unless the exact artifact is attached and independently checked.
- The 135.21W stress-test GPU power figure, unless raw power logs are attached and independently checked.
- Latency under load or production TPS/RPS.
- Behavior on non-synthetic, dirty, or schema-changing real-world telemetry.
- Comparison against RAG, vector-store, or long-context baselines beyond the documented replay calculation.
- Production engine internals.

## Output Format

Return a table with these columns:

| Objective | Status (PASS / FAIL / PARTIAL / NOT TESTED) | Evidence | Measured Values | Limitations | Requirement for Full Validation |

Then end with:

1. A plain list of claims independently supported by this bundle.
2. A plain list of claims that remain project-asserted only.
3. A plain list of skipped or not-tested steps.

## Constraints

- Do not accept "matches documentation" as a result. Report actual numbers from inspected files or executed commands.
- Do not extrapolate results from the 3k run to the 100k run, or the 100k run to the 3k run.
- Do not treat comments, docs, or marketing copy as proof of behavior. Use inspected files or runtime output.
- Unsupported conclusions are not permitted.
