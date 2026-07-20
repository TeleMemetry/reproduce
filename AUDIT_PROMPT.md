# Independent Audit Prompt

Use this prompt with ChatGPT, Claude, Gemini, Codex, or another technical reviewer after running the TeleMemetry reproduce kit. It is intentionally skeptical. The goal is to identify what the public harness proves, what it does not prove, and what remains project-asserted until independently reproduced.

## Role

You are a skeptical technical reviewer validating claims made by the TeleMemetry reproduce repo and its published benchmark artifacts. Your job is to find where the evidence is solid and where it is not. Do not confirm the publisher's framing unless the artifacts support it.

## Context

TeleMemetry claims verified, exact-match operational telemetry recall, bounded active context per turn versus full-history replay, and publishes:

- A flagship Isaac Lab run: 100,000 / 100,000 verified outputs, 278 average context tokens per turn, 3,548x replay reduction, and 135.21W stress-test GPU power.
- A public reproduce repo default run: 3,000 turns, 10 fields, 20 episodes, expected 3,000 / 3,000 verified, about 52.96 average tokens per turn, and about 192.79x replay reduction.
- A preserved CelesTrak snapshot: 1,329 / 1,329 probes, 100% recall, dated 2026-06-01, explicitly labeled as not a currently running feed and not a sealed artifact.

Validate each objective independently. Do not assume a prior objective holds.

## Objectives

### 1. Reproduce the default benchmark

- Clone the repo fresh in an isolated environment with no cached state.
- Run `python run.py`, then `python verify.py results/latest` per the README.
- Confirm the actual output numbers: verified turns, final failures, average tokens per turn, and replay reduction.
- Report exact numbers produced. Flag any deviation, however small, and do not round in the publisher's favor.

### 2. Inspect the verification logic

- Read `verify.py`, `run.py`, and any exactness-comparison code.
- Confirm verification is exact-match against stored reference values, not fuzzy or threshold matching.
- Confirm the failure definition in code matches the docs: final output miss, missing evidence packet, or integrity failure.
- Flag any verification path that is skipped, mocked, short-circuited, or merely documented instead of executed.

### 3. Validate token and replay-reduction math

- Locate where the full-history replay baseline is calculated.
- Confirm whether it is calculated from the generated dataset and benchmark scope, or hardcoded as an assumed constant.
- State explicitly what the replay-reduction number includes and excludes.
- Confirm that storage, routing, hashing, packaging, and verification costs are separate system costs and not counted as model-visible context tokens.

### 4. Stress past the default scale

- Rerun with `--turns 10000 --fields 10 --episodes 20`, or higher if resources allow.
- If the public harness enforces a documented cap, report the cap and explain why the cap exists rather than treating the cap itself as a failure.
- Report whether recall stays at 100% or degrades, and at what scale failures first appear.
- Do not extrapolate a 3k result to the 100k flagship run.

### 5. Check for scope leakage

- Confirm the benchmark dataset is deterministic and synthetic as claimed.
- Confirm no network calls, credentials, or external dependencies are required for the local default run.
- Flag anything that requires elevated privileges, network access, credentials, or undisclosed services.

### 6. Check SHA256 receipt integrity

- Independently recompute SHA256 hashes for result artifacts against `manifest.json`, outside any tooling the repo provides.
- Confirm receipts describe final artifacts.
- State clearly that same-storage receipts detect ordinary artifact changes, but do not by themselves prove protection against simultaneous malicious replacement of both artifact and receipt.

### 7. Identify what remains unverified

Explicitly list every claim made in the site, docs, or result package that this repo does not and cannot validate, including:

- The 100k Isaac Lab flagship run itself.
- The CelesTrak preserved snapshot or any live feed.
- The 135.21W stress-test GPU power figure.
- Latency under load or production TPS/RPS.
- Behavior on non-synthetic, dirty, or schema-changing real-world telemetry.
- Comparison against RAG, vector-store, or long-context baselines beyond the documented replay calculation.
- Production engine internals.

## Output Format

For each objective, return:

- `PASS`, `FAIL`, or `PARTIAL`
- actual measured numbers
- evidence inspected
- one sentence on what would need to change for full validation

End with a plain list of claims that remain project-asserted only, with no independent reproduction from this repo.

## Constraints

- Do not accept "matches documentation" as a result. Report actual numbers.
- Do not extrapolate results from the 3k run to the 100k run, or the 100k run to the 3k run.
- Do not treat comments, docs, or marketing copy as proof of behavior. Trace actual execution.
- Flag elevated privileges, network access, credentials, hidden services, or undisclosed dependencies.
