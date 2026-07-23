# AI Audit Prompt

You are reviewing a TeleMemetry public reproduction result package. If file uploads are limited, attach `AI_AUDIT_PACKET.md` first. If your AI assistant accepts multiple files, attach the listed files individually. If it accepts ZIP files, the evidence-bundle ZIP is okay. Do not answer from this prompt alone.

Universal single-file option:

- `AI_AUDIT_PACKET.md`

Minimum multi-file option:

- `metrics.json`
- `manifest.json`
- `VERIFY.txt`
- `RESULT_SUMMARY.txt`

Full audit files, if the assistant accepts larger files:

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
