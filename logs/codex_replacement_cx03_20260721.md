# Codex replacement CX-03 execution log

## CX-03B unified execution

- Main branch now defaults to `EIA_AGENT_PROVIDER=codex`; `hermes` remains an explicit rollback provider.
- Added provider-neutral active run state: `active_agent_provider` and `active_agent_run_id`. The legacy Hermes fields remain only for old tasks and actual Hermes runs.
- Main HB nodes, PREP-INGEST, file validation, web search, feedback revision, and auxiliary Agent calls use the same `HttpAgentClient` contract.
- Codex node calls provide a strict output envelope with Markdown, JSON string, evidence references, limitations, and disclaimer. Invalid or process-only output fails the current node and does not advance `next_node`.
- Events are normalized as agent call, tool, usage, reasoning signal, context compaction, partial output, completion, failure, and stop events. Internal reasoning text is not persisted.
- Frontend state accepts provider-neutral run IDs and event names while retaining Hermes compatibility for rollback.

## Contract smoke result

`scripts/cx03_codex_contract_smoke.py` passed using an in-process fake Agent client in isolated temporary data directories:

- PREP-INGEST, HB-PT-000, HB-PT-002, and HB-PT-009 completed with validated envelopes.
- Tool, usage, context-compaction, and node-complete events were observed.
- A failed run left the task failed at the same `next_node`.
- FILE-VALIDATION persisted through the Codex auxiliary path.
- HB-PT-000 feedback revision persisted a Codex result and kept the next node at HB-PT-001.

No live backend or Hermes process was restarted or sent a migration test request. Next step is isolated real-data Gate B against the CX-02 Codex sidecar image.

## Developer instruction correction

- Root cause of the first real HB-PT-002 run: the business tool policy was embedded in `user_input`, while the Sidecar's actual `developer_instructions` field was empty. The model had both terminal and native Web Search available and chose repeated `commandExecution`/`curl` searches.
- Added `prompts/agent_developer_instructions.txt` and pass it through `HttpAgentClient.create_run(instructions=...)`. The Sidecar passes it to Codex `thread_start(developer_instructions=...)`.
- The developer policy explicitly assigns discovery to native Web Search, local document work to Shell/OCR/vision, and exact-URL verification to page reading. It forbids replacing search with search-page HTML/JavaScript scraping.
- Removed the temporary fixed tool-operation limit after review. The runtime now relies on correct tool routing and completion validation, not an arbitrary call count.
- Contract smoke passed with assertions that every main, auxiliary, file-validation, and feedback request carried the developer instruction policy.
