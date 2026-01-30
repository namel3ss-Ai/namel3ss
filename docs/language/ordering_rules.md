# Ordering Rules

> This document defines the canonical ordering rules used across namel3ss outputs. It is authoritative and must remain stable.

## Scope
- Applies to IR construction, runtime manifests, explain packs, audit reports, and contract payloads.
- Ordering rules are deterministic; identical inputs must produce identical order.

## Canonical JSON Serialization
- Canonical JSON is produced with `namel3ss.determinism.canonical_json_dumps`.
- Dict keys are sorted by their string representation.
- Lists preserve order; tuples are serialized as lists.
- Sets are sorted by string and serialized as lists.
- `Decimal` values are normalized (integers become ints; otherwise a string).
- `Path` values are normalized to POSIX strings.
- Run payloads may drop run-only keys (for example `ui`) when canonicalized.
- Trace payloads scrub volatile keys (timestamps, ids) before canonicalization.

## Lists (general)
- Declaration lists (records, flows, jobs, pages, tools, AIs, agents) preserve source order.
- Statement lists preserve source order.
- Map/list literal items preserve source order.
- Capabilities are normalized by dedupe + sorted order.
- Tool exposure order preserves declaration order; duplicates are rejected.

## Maps (general)
- In-memory maps preserve insertion order.
- When serialized in canonical JSON, map keys are sorted by string.
- UI manifest actions are sorted by action id before serialization.

## Effects (record changes)
Record effects use the canonical order in `runtime.records.inspection`:
- Records are processed in program record declaration order.
- Actions are emitted in this order: `create`, `update`, `delete`.
- `ids` are sorted by `sorted_record_ids` (numeric before string; decimals normalized).

## Audit Entries
Audit decision ordering is deterministic and fixed:
1. Upload state decisions: upload names sorted; entries sorted by name then checksum.
2. Upload trace decisions: trace order.
3. Ingestion decisions: upload ids sorted.
4. Review decisions: trace order, then inferred skip decisions from ingestion map order.
5. Policy decisions: fixed order defined by policy actions list.
6. Retrieval decision (if present): appended last; per-upload decisions ordered by quality
   (`block`, `warn`, `pass`) then upload id.

## Explain Output
### UI explain (`n3 see`)
- Pages are in manifest order.
- Elements are emitted in a depth-first walk of page elements.
- Actions are ordered by action id.
- `what_not` lines preserve build order.

### Flow explain (`n3 explain`)
- Execution steps follow runtime execution order.
- Tool entries are grouped `allowed`, `blocked`, `errors` in that order; each group is sorted.
- `expected_effects` preserves first-seen order across steps, tools, and memory.
- `reasons` and `what_not` are deduped, first-seen order, and truncated to a fixed limit.

### Execution explain graph
- Nodes are sorted by id.
- Edges are sorted by `(src, dst, kind, note)`.
- Summary dict keys are sorted.

### Memory explain graph
- Nodes are sorted by `(kind, id)`.
- Edges are sorted by `(src, dst, kind, note)`.
- Space and reason ordering use explicit ordering tables in memory explain helpers.

### Composition explain
- Call tree order follows trace order.
- Pipeline and orchestration runs preserve trace order.
- All outputs are canonical JSON.
