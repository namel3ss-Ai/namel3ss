# Studio

Studio is an optional inspection lens for namel3ss. It stays fast and minimal while surfacing architecture, state, traces, and normalized guidance. It never introduces studio-only semantics; every payload mirrors the CLI.

## CLI parity
- Manifest intent matches `n3 ui --json` (ordering, ids, normalized fields).
- Validation errors and warnings match `n3 check`.
- Why panel mirrors `n3 explain --json`.
- Actions list matches `n3 actions --json`.
- Traces are the runtime contract traces (no studio-synthesized events).
- Authentication and authorization events appear in the Traces panel when present.

## Graph
- Visual map of the app root, local capsules, and installed packages.
- Click a node to see source, version/license (for packages), and exported symbols.
- Data comes from the same engine graph and exports used by `n3 graph` and `n3 exports`.

## Modules
- Shows module files loaded from use module statements.
- Lists merge order, provided items, and overrides.
- Module traces are visible under the Traces tab.

## Trust
- Engine status: active target, proof id, build id, persistence target.
- Proof: open and copy the latest proof JSON.
- Verify: run "Verify for prod" and inspect top failures.
- Secrets: list missing/available secret names (values are never shown).
- Observe: recent events (last 50).
- Explain: a compact summary of why the current state is allowed.
- Why: same payload as `n3 explain --json`, rendered for quick reading.

## Data & Identity
- Persistence target and descriptor (URLs are redacted).
- Migration status (plan id, pending state, breaking flags).
- Export/import summaries for the last data snapshot actions.
- Identity mode (none/dev defaults/runtime required).
- Authentication summary (source, token status, session state).
- Identity summary (subject, roles, permissions, trust_level).
- Tenant scoping status and keys.
- Audit timeline with flow/action filters and text search.

## Errors & guidance
- Errors panel uses normalized error payloads (same what/why/fix hints as CLI).
- Fix hints are deterministic and never apply changes automatically.
- Studio does not add studio-only fixes or validations.

## Observability
- Logs show structured log events with levels and fields (redacted).
- Tracing shows deterministic spans for actions, jobs, capabilities, and packs.
- Metrics lists counters and logical timings with stable ordering.
- Metrics summary surfaces health, quality, failures, and retries from observability outputs.

## Formulas + Explain (calc)
- Formulas tab renders calc blocks with a Code/Formula toggle for math-friendly display.
- Explain tab shows deterministic calc-line explanations (inputs, steps, outputs).
- Copying from Formula View returns the original calc line text.

## Agents
- Agent Builder scaffolds agents from deterministic patterns (no free-text config).
- Agents panel lists declared agents and supports single or parallel runs.
- Agent team intent (names, roles, order) mirrors the manifest contract.
- Timeline shows trace-backed stages (memory, tools, output, merge, handoff).
- Memory facts summaries include keys, counts, and last_updated_step (no raw values).
- Memory Packs and Handoff panels expose active pack selection and packet previews.
- Explain actions show deterministic reasons for tool decisions, merge outcomes, and handoffs.

## Registry
- Registry tab lists available capability packs from configured registries.
- Each pack shows version options, intent text, capabilities, risk, and signature status.
- Trust status and policy reasons explain why a pack is allowed or blocked.
- No raw keys or secrets are displayed.

## Deploy
- Deploy tab shows the active build and target, last ship action, and rollback availability.
- Build summaries include entry instructions and artifact locations.
- Environment summary lists required vs optional variables with redacted guidance.

## Learning Overlay
- Toggle **Learn** to highlight key panels with short explanations.
- Tooltips link to one-page docs under `docs/models/`.
- The overlay is optional and never blocks normal use.

## Packages
- Search the official package index by name or keyword.
- View package info and copy install commands.
- Studio never auto-installs; it stays a discovery surface.

## Notes
- Studio rendering and inspection are read-only; only explicit action runs execute flows.
- All outputs are redacted and deterministic.
- Studio does not change runtime behavior or introduce new semantics.
