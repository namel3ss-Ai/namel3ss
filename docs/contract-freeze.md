# Contract Freeze

## Scope
This document is the authoritative list of frozen public contracts. Any change to these contracts requires compatibility review and migration planning.

## Frozen contracts
- Grammar and semantics: docs/language/grammar_contract.md
- Backward compatibility rules: docs/language/backward_compatibility.md
- CLI commands and output shapes: docs/cli-*.md and tests/fixtures/cli/help.txt
- Explain and audit outputs: docs/trust-and-governance.md and docs/trace-schema.md
- Observability outputs: docs/observability.md and tests/fixtures/observability_summary.json
- Template contracts and index: docs/templates.md and src/namel3ss/templates/
- Studio stable UI surfaces: docs/studio.md and tests/studio/test_studio_guardrails.py
- Capability and policy enforcement: docs/capabilities.md and docs/language/backend-capabilities.md

## Guardrails
CI is authoritative. The following checks are required to stay green:
- Python compile checks
- Test suite (pytest)
- Responsibility checks
- Line limit checks
- Repo cleanliness checks

## Change control
- Breaking changes require explicit migration tooling and opt-in.
- Additive changes must not alter existing semantics or outputs.
- Removal or modification of guardrails is treated as a breaking change.
