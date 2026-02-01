# Core stable graduation

> This document defines the graduation gate for core stable and is normative.

## Definition
Core stable means the core language surface, compiler behavior, and safety gates are frozen and enforced.
All changes to the frozen surface require an explicit breaking-change process.

## Frozen surface
- Grammar contract and grammar snapshot are authoritative and must match parser behavior.
- Parsing, recovery, and diagnostics ordering are deterministic and contract-locked.
- Incremental parse output equals full parse output for final text.
- Type system baseline is frozen (no silent widening or inference changes).
- Lowering and IR output are deterministic with canonical ordering.
- Purity, identity, mutation, and secrets guards are enforced with deterministic diagnostics.
- Repository hygiene is enforced; repo_clean must always pass.
 - Fuzz and property tests remain deterministic and stable across runs.

## Evolvable surface
- Performance optimizations that do not change outputs or diagnostics.
- New features that go through the breaking-change process and update contracts.
- Tooling and docs improvements that do not alter runtime or compiler semantics.

## Breaking change handling
- Any change to the frozen surface requires an accepted RFC.
- Contracts and goldens must be updated together, with clear justification.

## Graduation gate
Core stable is achieved only when all graduation checklist items pass in CI and for reference apps.

## Graduation checklist
- Grammar contract snapshot matches parser behavior.
- Grammar coverage gates pass.
- Parser resiliency and recovery tests pass.
- Incremental parsing contract tests pass.
- Fuzz and property determinism gates pass.
- Determinism and safety gates pass (purity, identity, secrets, mutation).
- Lowering produces canonical IR and explain outputs remain stable.
- Repository cleanliness gate passes.
- Reference apps pass the same core gates (parse, verify, repo_clean).

## CI enforcement
- `release-gate` runs the full test suite and core contract gates.
- `graduation-core-stable` runs core stable contract tests, reference apps, and repo_clean.
