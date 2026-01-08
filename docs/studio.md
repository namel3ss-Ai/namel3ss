# Studio

Studio is the command center for namel3ss. It stays fast and minimal while surfacing the architecture, trust posture, data/identity state, and guided fixes you can apply safely.

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
- Why: plain-English summary of architecture + access rules.

## Data & Identity
- Persistence target and descriptor (URLs are redacted).
- Identity mode (none/dev defaults/runtime required).
- Tenant scoping status and keys.
- Audit timeline with flow/action filters and text search.

## Fix
- Diagnostics list with severity, location, and message.
- One-click fixes show a preview diff; apply only after confirmation.
- Rename with preview + apply using the same editor patch format as `n3 editor`.

## Formulas + Explain (calc)
- Formulas tab renders calc blocks with a Code/Formula toggle for math-friendly display.
- Explain tab shows deterministic calc-line explanations (inputs, steps, outputs).
- Copying from Formula View returns the original calc line text.

## Learning Overlay
- Toggle **Learn** to highlight key panels with short explanations.
- Tooltips link to one-page docs under `docs/models/`.
- The overlay is optional and never blocks normal use.

## Packages
- Search the official package index by name or keyword.
- View package info and copy install commands.
- Studio never auto-installs; it stays a discovery surface.

## Notes
- Studio uses engine terminology (not runtime).
- Studio rendering and inspection are read-only; only explicit action runs execute flows.
- All outputs are redacted and deterministic.
- Guided fixes never change files until you click Apply.
