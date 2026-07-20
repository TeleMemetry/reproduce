# AI Audit Prompt

You are reviewing a TeleMemetry public reproduction result package.

Inspect the attached or pasted files:

- `metrics.json`
- `manifest.json`
- `VERIFY.txt`
- `dataset.jsonl`
- `evidence_packets.jsonl`
- `outputs.jsonl`

Answer in plain language:

1. Did the run verify exact recall for every turn?
2. What was the average bounded evidence-packet token estimate per turn?
3. What full-history replay baseline was used?
4. What replay reduction ratio was reported?
5. Do the SHA256 receipts allow reviewers to detect artifact changes?
6. What claims are supported by this package?
7. What claims are not supported by this package?

Important boundaries:

- This is a scoped deterministic public benchmark.
- It does not expose TeleMemetry production engine internals.
- It does not prove universal semantic memory, chatbot reasoning quality, robotics safety, AV certification, or general power savings.
- It proves scoped exact operational-state recall mechanics with bounded evidence packets and verifiable artifacts.
