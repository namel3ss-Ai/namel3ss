# Native Boundary

This directory holds the native boundary scaffolding for namel3ss. Native code may accelerate mechanics but does not own meaning. Python remains the semantic authority.

## Build
- `cargo build --manifest-path native/Cargo.toml`
- `python tools/native_check.py` (build check with isolated target dir)
- `python tools/native_verify.py` (build + load verification)

## Determinism Rules
- No time, randomness, environment, or host paths in outputs.
- Canonical bytes only; stable ordering is required.
- No floating-point values in the ABI.

## ABI
- Header: `native/include/namel3ss_native.h`
- Buffers use explicit lengths.
- Output buffers are native-owned and must be released with `n3_free`.
- Chunk planning uses `n3_chunk_options` (integer-only).

## Enablement
- Native use is opt-in via `N3_NATIVE`.
- If a library path is provided, set `N3_NATIVE_LIB` to the shared library location.
- If `N3_NATIVE_LIB` is unset, the loader checks `namel3ss/runtime/native/lib`.
- Default behavior is Python fallback.

## Packaging
- Build the native library and copy it into `src/namel3ss/runtime/native/lib/`.
- Wheels include `lib/*` when present; pure-Python installs remain supported.
- `N3_NATIVE` must be set to opt in at runtime.

## Semantics
- Grammar, lowering, ordering, and explain contracts live in Python.
- Native code must not define schemas, error messages, or ordering rules.
