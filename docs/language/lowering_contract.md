# Lowering Contract

> This document defines the canonical lowering pipeline from AST to IR. It is authoritative and must remain stable.

## Scope
- Applies to the English-first sugar lowering (`namel3ss.parser.sugar.lower`) and IR lowering (`namel3ss.ir.lowering`).
- Lowering is structural: it preserves meaning and determinism; it does not introduce new semantics.
- Python semantics are the reference truth for all lowering behavior.

## Canonical Pipeline (ordered)
Lowering runs in the following fixed order. Reordering is a breaking change.

### 1) Parse to AST
- Parsing follows `docs/language/grammar_contract.md`.
- The parser produces an AST with source locations on every node.

### 2) Sugar to core AST (when enabled)
- English-first sugar is lowered into core AST before IR lowering.
- Sugar lowering is deterministic and does not change execution semantics.
- Sugar lowering may expand a single statement into multiple core statements; ordering follows source order.

### 3) AST to IR (program-level lowering)
The program lowering order is canonical:
1. Require a spec declaration; missing spec is a hard error.
2. Lower record declarations into record schemas (order preserved).
3. Lower identity declaration (if present).
4. Lower tool declarations into a tool map (duplicate names are errors).
5. Lower AI declarations into an AI map (provider/tool validation is enforced).
6. Lower agent team declaration (if present).
7. Lower agent declarations into an agent map (validated against AI map and team).
8. Lower function declarations into a function map.
9. Lower flow contracts into a contract map.
10. Lower flow bodies into IR flows.
11. Lower job bodies into IR jobs.
12. Validate flow names, contract signatures, composition rules, and purity.
13. Validate declarative flows against record schemas and tools.
14. Normalize capabilities (dedupe + sort) and enforce required capabilities.
15. Normalize pack allowlist (dedupe while preserving order).
16. Build UI pack index and UI pattern index.
17. Lower pages into IR pages, expanding UI packs and UI patterns.
18. Enforce unique page names.
19. Compute theme runtime support by scanning for theme changes.
20. Normalize UI settings and resolve the theme setting for IR.
21. Build the IR `Program` with preserved source locations and attach the pack allowlist.

### 4) AST to IR (flow-level lowering)
- Non-declarative flows lower each statement in source order.
- Declarative flows set `declarative=true`, keep `steps`, and leave `body` empty.
- Flow `requires`, `audited`, and `purity` are preserved exactly from the AST.

### 5) AST to IR (expression/statement lowering)
- Each AST node lowers to its corresponding IR node with `line`/`column` preserved.
- Expression and statement lists preserve source order.
- Lowering never reorders map/list literals.

## Preserved vs Erased
**Preserved**
- Source order of declarations, statements, and items.
- Names, identifiers, and literal values.
- Source locations (`line`, `column`) on all lowered nodes.
- Declarative flow steps, including field ordering.

**Erased**
- Whitespace, indentation, and comments.
- Sugar-only syntax (expanded into core AST statements).
- Lexer token types (only semantic values remain).

## Canonical Invariants
- Lowering is deterministic for identical inputs.
- Errors raised during lowering must match existing behavior and messages.
- Lowering must not introduce new IR node kinds or reorder existing structures.
- All optional IR fields are either populated or set to `None` (never omitted).
