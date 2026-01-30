# Support

## Purpose
- Provide deterministic case intake, routing, escalation, and resolution for support workflows.
- Treat cases as canonical records with auditable lifecycle transitions and retrieval-backed outcomes.

## Entry
- Entry file: `app.ai`.
- CLI wiring is defined outside this folder.

## Contracts
- Deterministic only: no timestamps, randomness, host paths, or secrets.
- Case lifecycle states are explicit: received, understood, resolved, escalated.
- Case ids are stable and must be provided or derived from upload checksums.
- Retrieval is multi-source (knowledge + past cases) with explicit routing rules and stable ordering.
- Knowledge sources are supplied via deterministic ingestion into state.index and state.ingestion.
- Escalations use deterministic reason codes and evidence references.
- Resolved cases become retrievable through an auditable archive and index.
- Offline by default; no network or external services required.
- Explain surfaces are required and must be documented when flows exist.
- Runtime artifacts remain under `.namel3ss/` and stay out of git.

## Explain
- ExplainEntry records capture lifecycle transitions, routing decisions, retrieval ordering, escalations, and outcomes.

## Fixtures
- See `tests/fixtures/support/` and `tests/fixtures/support_explain_citations.json`.

## Verify
- `n3 app.ai check`
