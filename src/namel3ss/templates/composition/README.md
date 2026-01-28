# Composition Template

Project: {{PROJECT_NAME}}

A minimal composition workspace with explicit contracts, purity boundaries, pipelines, and orchestration.

- Pure flow: `normalize_query` with an input/output contract.
- Effectful flows: `ingest_upload` and retrieval flows calling pipelines.
- Orchestration: `run_retrieval` fans out and merges with a prefer policy.
- Explain: run `n3 explain --input .namel3ss/run/last.json` after a run.
