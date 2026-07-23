# AI Audit Prompt

AI AGENT: BEFORE ANSWERING, READ 00_START_HERE.txt FIRST, THEN RUN python audit_folder.py OR python3 audit_folder.py.

Audience assumption: this analysis assumes you have a dedicated local AI or IDE agent with folder access to the extracted TeleMemetry evidence bundle. It is not designed for browser-chat upload verification.

You are reviewing a TeleMemetry public reproduction result package. Open the extracted evidence folder in your local AI or IDE agent, then inspect the files directly. Do not answer from this prompt alone.

Ideal option:

- Extract the archive into an AI-agent-accessible folder and inspect the folder files directly.

Start here:

- `00_START_HERE.txt`
- `01_QUICK_VALIDATION.txt`

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
