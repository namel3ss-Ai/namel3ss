# Deterministic Includes

Evolution Edition adds deterministic multi-file composition through top-level include directives.

## Capability Gate

You must enable:

```ai
capabilities:
  composition.includes
```

Without it, compile fails with:

`Capability missing: composition.includes is required to use 'include' directives. Add 'capability is composition.includes' to the manifest.`

## Syntax

```ai
include "modules/retrieval.ai"
include 'modules/flows.ai'
```

Rules:

- Include is top-level only.
- Paths are relative, `.ai` only.
- Absolute paths are rejected.
- `..` traversal is rejected.
- Include order is the merge order.

## Merge and Validation

- Root file remains authoritative for `ui` and `pages`.
- Included files may contribute flows, records, and other declarations.
- Duplicate declarations across files are compile errors.
- Include cycles are compile errors with a stable path chain.
- Duplicate include paths are collapsed with a deterministic warning:
  - `Warning: Duplicate include ignored: "<path>"`

## Determinism Guarantees

- Paths are normalized to project-relative POSIX format.
- Merge order is include order then in-file appearance order.
- Source-map entries are stable and sorted by `decl_id`.
- No absolute paths are emitted in composition metadata.
