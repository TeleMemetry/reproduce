# Launchable Boundary

This repository powers the TeleMemetry Memory Rail Demo.

It is intentionally narrow:

- scoped deterministic operational recall
- bounded evidence packets
- exact verification
- SHA256 result artifacts
- public reproduction without production engine internals

It is not the RAG comparison benchmark and should not grow into that benchmark.

## Related Launchables

| Launchable | Repository | Status | Purpose |
|---|---|---|---|
| TeleMemetry Memory Rail Demo | `TeleMemetry/reproduce` | active | One-click scoped bit-perfect recall verification. |
| TeleMemetry vs RAG Retrieval Benchmark | `TeleMemetry/rag-comparison` | scaffolded separately | Fair comparison of exact operational telemetry retrieval against a lightweight RAG baseline. |
| Semantic Memory Benchmark | not started | future | Narrative or semantic memory benchmark; lower priority because scoring is more subjective. |

## Rule

Keep this repo fast, simple, and auditable. Add comparison logic in the separate RAG comparison repository.
