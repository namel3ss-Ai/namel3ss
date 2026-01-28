# Composition Contract

> This document defines the composition rules for flows and pipelines. It is authoritative and must remain stable.

## Scope
- Composition covers flow-to-flow calls and flow-to-pipeline calls.
- Composition is a language contract; it does not add features or alter runtime behavior.
- Composition rules apply to parse, build, and runtime validation.

## Definitions
- **Flow call**: `call flow "<name>":` with explicit `input:` and `output:` blocks.
- **Pipeline call**: `call pipeline "<name>":` with explicit `input:` and `output:` blocks.
- **Contract**: The declared input/output signature for a flow or pipeline.

## Resolution Rules
- Flow and pipeline names are string literals; names are not computed or dynamically resolved.
- Flow calls resolve to flows declared in the same program.
- Flow calls require a matching `contract flow` declaration.
- Pipeline calls resolve to the pipeline contract registry.
- Resolution is static: unknown flows, missing contracts, or unknown pipelines are rejected during build.
- Runtime re-validates resolution and signatures for safety; it must report the same error conditions.

## Deterministic Ordering
- Call graphs must be acyclic; recursion (direct or indirect) is rejected.
- Inputs and outputs are ordered and must match the contract order exactly.
- Argument evaluation follows source order; output selection follows the output list order.
- Flow call identifiers are assigned deterministically in evaluation order.

## Boundary Semantics
- A flow call creates a fresh local scope containing `input` and (when present) `secrets`.
- Callers do not share locals with callees; only declared inputs cross the boundary.
- State is shared through explicit state operations; composition adds no hidden state channels.
- Contracts define the only allowed input and output fields.

## Trace and Explain Linkage
- Flow calls emit trace events:
  - `flow_call_started` with `flow_call_id`, `caller_flow`, `callee_flow`, inputs, and outputs.
  - `flow_call_finished` with `flow_call_id`, `caller_flow`, `callee_flow`, and status.
- Pipeline calls emit execution steps: `pipeline_call_start`, `pipeline_call_end`, and `pipeline_call_error`.
- Pipeline calls emit pipeline trace events: `pipeline_started`, `pipeline_step`, and `pipeline_finished` with deterministic step ids and checksums.
- Pipeline calls also emit pipeline-specific traces (for example ingestion and retrieval events).
- Explain surfaces must reflect the same call order and identifiers as traces.

## Allowed Behaviors
- Static resolution of flow and pipeline names.
- Explicit input/output mapping that matches the contract order.
- Deterministic execution and trace emission for composed calls.
- Calls to pipelines only through declared pipeline contracts and required capabilities.

## Forbidden Behaviors
- Recursion or cyclic flow call graphs.
- Dynamic name lookup or computed call targets.
- Flow calls without `contract flow` declarations.
- Missing, extra, or out-of-order inputs/outputs.
- Composition inside functions.
- Composition inside parallel tasks.
- Implicit state sharing across boundaries.
- Capability escalation through composition.

## Stability Guarantees
- Existing flow and pipeline call syntax remains stable.
- Contract-ordered input/output validation is frozen.
- Trace event shapes and ordering for flow calls are stable.
- Future additions may introduce new pipeline contracts but must not change existing call semantics.
