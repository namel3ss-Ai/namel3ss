# Native Boundary Contract

This contract defines the native boundary for namel3ss. Native code may accelerate mechanics but may not own meaning. Python semantics remain the authority for all observable behavior.

## Authority
- Python is the semantic authority for parsing, lowering, runtime behavior, and output contracts.
- Native code is an optional accelerator; it must not define language meaning, ordering rules, or schema ownership.

## Allowed Responsibilities
- Pure mechanical transforms that are already defined by Python contracts.
- Byte-level operations such as scanning, hashing, or normalization once defined by Python behavior.
- Buffer handling that preserves canonical ordering and deterministic bytes.

## Forbidden Responsibilities
- Changing grammar, IR shape, ordering rules, or output schemas.
- Introducing new errors, error messages, or diagnostics.
- Reading time, randomness, environment, host paths, or network state.
- Performing file system or network I/O.

## Determinism Constraints
- Same input bytes must produce identical output bytes.
- No timestamps, randomness, or environment-dependent data.
- Stable ordering is enforced at the boundary; no platform-dependent sorting.
- No floating-point values in the boundary ABI.

## Memory Ownership
- Input buffers are owned by the caller and are immutable.
- Output buffers returned by native are owned by native and must be released with `n3_free`.
- The boundary uses explicit lengths for all buffers; no sentinel termination.

## Error Policy
- Native returns only stable status codes.
- Status codes are mapped to existing Python diagnostic codes; Python owns messages.
- `NOT_IMPLEMENTED` indicates a clean fallback to Python.

## Status Codes
- `OK`
- `NOT_IMPLEMENTED`
- `INVALID_ARGUMENT`
- `INVALID_STATE`
- `ERROR`
