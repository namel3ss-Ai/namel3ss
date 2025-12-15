# Namel3ss Roadmap (Phases 0–9)

This roadmap captures the CTO plan for reaching a stable v3 of Namel3ss with deterministic defaults and explicit AI boundaries.

## Phase 0 — Foundations
- Repository scaffold (packages, docs, CI, line limit guard) and editable install path.
- Define Core v1 contract (keywords, forbidden phrases, determinism boundary).

## Phase 1 — Lexing
- Tokenize English-first syntax with clear token classes and error recovery hooks.
- Emit precise, human-readable diagnostics with positions and suggested fixes.

## Phase 2 — Parsing & AST
- Build a deterministic parser producing a typed AST with source spans.
- Establish AST invariants and validation passes (duplicates, shadows, unreachable constructs).

## Phase 3 — Semantic Analysis
- Resolve names, scopes, and imports; enforce language contracts.
- Introduce static checks for determinism boundaries and AI entrypoints.

## Phase 4 — IR Definition
- Design a minimal, stable IR for lowering AST constructs.
- Add IR validators and snapshot-friendly serialization for debugging.

## Phase 5 — Runtime Core
- Implement deterministic runtime primitives (control flow, data, errors).
- Add tracing hooks for execution steps and deterministic replay.

## Phase 6 — CLI & Tooling
- Provide `namel3ss` CLI for compile, run, format, and inspect commands.
- Build developer ergonomics: watch mode, structured errors, and help texts.

## Phase 7 — Standard Library (Deterministic)
- Ship minimal stdlib: data structures, IO wrappers, time, and math with explicit determinism guarantees.
- Harden module loading, configuration, and reproducibility defaults.

## Phase 8 — AI Boundary & Augmentation
- Add explicit AI blocks/calls with budgeting, caching, and audit logs.
- Provide testing harnesses for AI paths with deterministic fallbacks and fixtures.

## Phase 9 — v3 Hardening & Release
- Optimize performance (profiling, caching, incremental builds).
- Finalize documentation, compatibility promises, and release packaging for v3.

