# TeleMemetry Reproduce

Audience assumption: this analysis assumes you have a dedicated local AI or IDE agent with folder access to the extracted TeleMemetry evidence bundle. It is not designed for browser-chat upload verification.

Public reproduction kit for scoped TeleMemetry-style verified recall benchmarks.

This repo is intentionally small. It does not contain TeleMemetry production engine internals, private telemetry, credentials, model weights, or customer data. It gives reviewers a safe way to generate a deterministic result package and verify the five public mechanics:

1. Exact recall correctness
2. Bounded evidence packets
3. Full-history replay avoidance accounting
4. SHA256 artifact receipts
5. Reproducible result packages for independent AI review

This repo is not the TeleMemetry vs RAG comparison benchmark. See `LAUNCHABLE_BOUNDARY.md` for the Launchable separation rule.

## Quick Start

### NVIDIA Brev Web Demo

Recommended Launchable setup:

- Source repo: `https://github.com/TeleMemetry/reproduce`
- Network secure link: `memory-demo` on port `7860`
- Optional startup command: `bash web_demo.sh`

User path:

1. Open the Launchable.
2. Open the `memory-demo` secure link.
3. Click **Run Demo**.
4. Read the result cards.

Why: this avoids terminal and notebook navigation. The browser UI runs the benchmark, verifies the package, and links to the start-here file, quick validation brief, result summary, AI audit prompt, metrics, and SHA256 manifest.

If the startup command is not available, open a terminal and run:

```bash
bash web_demo.sh
```

Then open the `memory-demo` secure link.

Expected result:

```text
3000 / 3000 verified recall
0 final failures
52.96 average bounded packet tokens per turn
192.79x replay reduction
```

### NVIDIA Brev Notebook Fallback

1. Open the Launchable.
2. Click **Open Notebook**.
3. Open `START_HERE.ipynb`.
4. Click **Run All**.

Why: this avoids terminal knowledge. The notebook runs the benchmark, verifies the package, and prints the result summary.

Expected result:

```text
Verification passed
Verified turns: 3000 / 3000
Final verified output failures: 0
Replay reduction ratio estimate: 192.79x
```

### Terminal

```powershell
python run.py
python verify.py results\latest
```

On Linux or NVIDIA Brev:

```bash
python3 run.py
python3 verify.py results/latest
```

The default run uses:

- 3,000 turns
- 10 structured fields
- 20 episodes
- deterministic public telemetry
- no external dependencies
- no credentials

## What It Produces

Each run writes a timestamped folder under `results/` and updates `results/latest`.

Expected files:

- `dataset.jsonl` - deterministic source telemetry records
- `evidence_packets.jsonl` - bounded packets delivered per turn
- `outputs.jsonl` - final verified outputs
- `metrics.json` - recall, token accounting, replay reduction, and run scope
- `manifest.json` - file sizes and SHA256 receipts
- `VERIFY.txt` - human-readable verification summary
- `RESULT_SUMMARY.txt` - plain-language result summary
- `00_START_HERE.txt` - first file for humans and folder-aware local AI or IDE agents
- `01_QUICK_VALIDATION.txt` - short validation brief for executives, engineers, and AI agents
- `README.md` - evidence-bundle folder README
- `prompt.md` - prompt for a local AI or IDE agent with folder access
- `AUDIT_PROMPT.md` - skeptical audit prompt for challenging the result package and claim boundaries
- `validate_bundle.py` - zero-dependency quick validator for hashes, counts, exact matches, and token math

`verify.py` recomputes manifest hashes, source-record hashes, evidence-packet token estimates, replay-reduction math, and exact output matches from the generated artifacts.

## What It Proves

This kit proves that, within this public benchmark scope, a reviewer can:

- Recreate a deterministic telemetry dataset.
- Query one bounded evidence packet per turn.
- Verify every returned value against the stored reference value.
- Compare bounded packet tokens against a full-history replay baseline.
- Detect artifact changes with SHA256 receipts.

## What It Does Not Prove

This repo does not prove universal memory, chatbot memory, semantic reasoning quality, production robotics safety, AV certification, or power savings across all hardware.

It is a scoped reproduction path for operational-state recall mechanics.

## Credentials

Do not commit credentials.

This repo does not need TeleMemetry credentials. If a hosted Launchable later needs cloud credentials, enter them only into the cloud provider's secret manager or environment variable UI.

Never commit:

- `.env`
- API keys
- cloud tokens
- SSH keys
- session cookies
- private telemetry
- production configs
- generated result packages containing secrets

## NVIDIA Brev Launchable Target

The Launchable should do three things:

1. Clone this repo.
2. Open `START_HERE.ipynb`.
3. Let the reviewer click **Run All**.

If startup commands are supported, use:

```bash
bash launch.sh
```

Reviewers should be able to increase turns, fields, and episodes later:

```bash
python3 run.py --turns 10000 --fields 10 --episodes 20
```

## AI Review

After running the benchmark, open `results/latest` as a folder in a local AI or IDE agent. Start with `00_START_HERE.txt`, then `01_QUICK_VALIDATION.txt`. The prompt asks the AI to inspect the metrics, receipts, scope, and supported claims.

Fast path:

```bash
cd results/latest
python validate_bundle.py
```

For a tougher review, use `results/latest/AUDIT_PROMPT.md` after the agent has folder access. That prompt asks the reviewer to inspect the code path, token math, SHA256 receipts, scale limits, scope leakage, and claims that remain outside this public reproduction kit.

## License

No license is granted yet. Public visibility allows review under GitHub terms, but reuse rights are intentionally not granted until the IP boundary is finalized.
