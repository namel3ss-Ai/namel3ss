# Architecture Overview

Namel3ss is organized into strict layers with deterministic contracts.

## Layers

1. **Parser (`src/namel3ss/parser`)**
   - Converts source text into AST with explicit source locations.
2. **AST/IR (`src/namel3ss/ast`, `src/namel3ss/ir`)**
   - Normalizes language constructs into deterministic intermediate forms.
3. **Manifest/UI (`src/namel3ss/ui`)**
   - Produces stable manifest payloads and UI contracts.
4. **Runtime (`src/namel3ss/runtime`)**
   - Executes flows/actions and serves manifest/action endpoints.
5. **Studio/Web (`src/namel3ss/studio/web`)**
   - Developer surface for preview, diagnostics, and debugging.
6. **Tooling (`tools`, `scripts`)**
   - Quality gates, release automation, and maintenance scripts.

## Stability boundaries

- Public contract declarations: `src/namel3ss/lang/public_api.py`
- Internal boundary declarations: `src/namel3ss/lang/internal_api.py`
- Deprecation policy enforcement: `src/namel3ss/lang/deprecation.py`

## Determinism principles

- stable IDs derived from source and declaration path
- deterministic ordering for pages, actions, warnings, and manifests
- reproducible packaging outputs from identical inputs
- explicit errors for invalid input or unsupported behavior

## Governance links

- `GOVERNANCE.md`
- `docs/compatibility_policy.md`
- `docs/deprecation_policy.md`
- `SECURITY.md`

## Roadmap link

- `docs/roadmap.md`
