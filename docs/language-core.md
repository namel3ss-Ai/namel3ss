# namel3ss Core v1 Contract

## Contract status (public)
- Status: frozen
- Applies to: language core surface
- Freeze semantics: public contract; changes must be additive and explicitly documented

This document defines the stable Core v1 surface: keywords, forbidden phrases, and the determinism boundary between AI and non-AI execution. The goal is repeatable programs by default, with AI usage declared explicitly.

## Stable Keywords (v1)
The following keywords are reserved and stable for Core v1; do not repurpose or overload them:

```
module import from as expose
return break continue defer
let const mut
if else match when
for while loop in
struct enum type trait impl
raise try catch finally assert
async await spawn
use with
```

- Keywords must remain deterministic in semantics; any AI behavior must be opt-in and explicit.
- New keywords require a major version bump or an RFC; avoid soft-reserving casual English words.

## Forbidden Phrases (v1)
To keep the language precise and reproducible, the following phrases must not appear in the core syntax, stdlib APIs, or diagnostics:
- Ambiguity: “maybe”, “kinda”, “sorta”, “approximately”, “best effort”.
- Implicit magic: “do what I mean”, “guess”, “auto-fix”, “magic”, “random-ish”.
- Vague time/scale: “soon”, “eventually”, “later-ish”, “whenever”.
- Hidden AI: any phrase that implies silent AI involvement without explicit consent (e.g., “auto-prompt”, “implicit model”).

## Determinism Boundary (AI vs non-AI)
- **Default deterministic:** All code is deterministic unless wrapped in an explicit AI construct.
- **Explicit AI blocks:** AI work must be enclosed in a declared boundary (e.g., `ai { ... }` or `ask model ...` when introduced). Every AI boundary must spell out the model, budget, timeout, and fallback strategy.
- **Observable outputs:** AI outputs must be logged with prompts, parameters, and provenance so runs can be audited and replayed with fixtures.
- **Pure surfaces stay pure:** Deterministic functions cannot call AI boundaries directly; route through explicit adapter functions annotated as AI-capable.
- **Testing contract:** Provide deterministic fixtures for AI calls; tests must not rely on live models.
- **No hidden entropy:** Randomness, clocks, and IO with side effects must be explicit and injectable; never smuggle nondeterminism through defaults.

## Implementation Guardrails
- Preserve the keyword list in the lexer/parser and guard it with tests.
- Reject forbidden phrases at parse/validation time with clear, human-readable errors.
- Keep AI boundary handling centralized (single-responsibility modules) to avoid accidental leakage into deterministic paths.
- Document every AI-capable API with its determinism expectations and fallback behavior.
