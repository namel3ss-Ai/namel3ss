# IR Reference

## Overview
- Pipeline: **AST → IR → Engine**. The parser builds AST nodes, lowering converts AST to IR (in `src/namel3ss/ir/lowering/`), and the engine executes IR flows.
- IR lives in `src/namel3ss/ir/model/` and mirrors the language surface with deterministic shapes for execution.

## Program shape (`ir.model.program.Program`)
- `records`: list of record schemas.
- `flows`: list of `Flow` entries (control logic).
- `pages`: list of UI pages.
- `ais`: mapping of AI profiles.
- `tools`: mapping of tool declarations.
- `agents`: mapping of agent declarations.

## Flow
- `Flow`: `name`, `body` (list of statements).

## Statements (IR)
- `Let`: declare local, optional constant.
- `Set`: assign to local or state path.
- `If`: conditional branch.
- `Return`: stop flow and yield value.
- `Repeat`: fixed-count loop.
- `ForEach`: loop over list.
- `Match`: pattern equality branches with optional otherwise.
- `TryCatch`: execute try-body, catch `namel3ssError` into a variable.
- `Save`: persist current record state to store.
- `Find`: query records matching predicate.
- `AskAIStmt`: call AI profile with input, bind result.
- `RunAgentStmt`: run a single agent (AI + prompt).
- `RunAgentsParallelStmt`: run multiple agents (limit enforced).
- `ParallelAgentEntry`: helper entry for parallel calls.

## Expressions (IR)
- `Literal`: primitives (string, int, bool, etc.).
- `VarReference`: local lookup.
- `AttrAccess`: nested attribute/dict traversal.
- `StatePath`: access into `state`.
- `UnaryOp`: unary ops (e.g., `not`).
- `BinaryOp`: binary logical ops (`and`, `or`).
- `Comparison`: `eq`, `gt`, `lt`.
- `Assignable`: alias for `VarReference | StatePath`.

## Lowering
- Location: `src/namel3ss/ir/lowering/`.
- Converts AST (`namel3ss.ast.nodes`) into IR model nodes.
- Responsibilities split by domain: `expressions.py`, `statements.py`, `ai.py`, `records.py`, `pages.py`, `agents.py`, `program.py`.
- Guarantees deterministic IR shapes and preserves source locations for engine errors.

## Tiny .ai example (conceptual)
```
flow "hello":
  let name is "world"
  return name

page "Home":
  button "Run":
    calls flow "hello"
```

Conceptual IR:
- Program.flows: one `Flow(name="hello", body=[Let(name="name", ...), Return(...)])`
- Expressions: `Literal("world")`, `VarReference("name")`
- Runtime executes `Let` (binds local), then `Return` (stops flow, returns "world").
