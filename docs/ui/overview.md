# UX DSL overview

## Purpose
This document defines the UX DSL as a deterministic contract. It is a specification of behavior, not a tutorial.

## What the UX DSL is
- A declarative description of UI structure and interaction intent.
- A deterministic manifest surface with stable ordering and identifiers.
- An explainable contract surfaced through `n3 see` and Studio inspection.

## What the UX DSL is not
- A styling system or per-component appearance language.
- A runtime scripting surface or imperative UI logic.
- A place to encode flow logic, data mutation, or tool access.

## Determinism and explainability
- Manifest output is deterministic and bounded.
- Visibility, patterns, uploads, and accessibility decisions are explicit in explain output.
- No runtime UI mutation is required to understand or validate behavior.

## Relationship to flows and composition
- Flows express logic and side effects; UI declares intent and binds to flows.
- Composition is structural (pages, sections, containers) and does not alter logic.
- Explain surfaces unify UI structure with flow availability and requirements.

## Related UX contracts
- Uploads: [uploads.md](uploads.md)
- Conditional UI: [conditional-ui.md](conditional-ui.md)
- Reusable patterns: [patterns.md](patterns.md)
- Accessibility: [accessibility.md](accessibility.md)
