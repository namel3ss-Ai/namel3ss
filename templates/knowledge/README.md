# Knowledge

## Purpose
- Provide deterministic ingestion, retrieval, and cited answers for knowledge workloads.
- Define auditable add, update, and remove behavior for documents.

## Entry
- Entry file: `app.ai`.
- CLI wiring is defined outside this folder.

## Contracts
- Deterministic only: no timestamps, randomness, host paths, or secrets.
- Ingestion runs through the quality gate and writes reports and index entries into state.
- Document ids derive from input or the upload checksum; chunk ids follow `<upload_checksum>:<chunk_index>`.
- Updates remove prior index entries without full reindexing.
- Answers are grounded in retrieved sources; no answer is returned when no sources are found.
- Citations are required and reference provenance ids from retrieval.

## Explain
- ExplainEntry records capture ingestion decisions, retrieval normalization and ordering, and evaluation signals.
- Retrieval explain includes both raw and normalized queries plus ranking inputs and selected sources.
- DocumentChange, RetrievalReport, Answer, and Citation records provide the audit trail.

## Fixtures
None.

## Verify
- `n3 app.ai check`
