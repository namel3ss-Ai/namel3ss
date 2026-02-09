# RAG Headless Golden Path

This example demonstrates the canonical headless integration flow using the official SDK and strict contracts:

1. Fetch UI + actions (`GET /api/v1/ui?include_actions=1`).
2. Upload a document (`upload_select` action).
3. Trigger ingestion (`ingestion_run` action).
4. Run chat action.
5. Render citations + trust indicator from returned state/manifest.
6. Render retrieval evidence from deterministic retrieval fields.

The client reads deterministic payloads with:

- `contract_version: "runtime-ui@1"`
- typed `runtime_error` and `runtime_errors`
- typed `retrieval_plan`, `retrieval_trace`, and `trust_score_details`
- optional `contract_warnings` in Studio/dev when validation finds schema drift

No defensive normalization or custom glue logic is required.
