# Embedding Contract

This document defines the deterministic embedding boundary for namel3ss hosts.
It is the authoritative contract for using the C ABI from non-Python hosts.

## Scope

- Applies to the C ABI declared in `native/include/namel3ss_native.h`.
- Applies to all host integrations that call native functions directly.
- Python remains the semantic oracle; native execution is mechanical only.

## Lifecycle

- No global initialization is required.
- Each ABI call is independent and must be provided valid inputs.
- Hosts must release native-owned output buffers via `n3_free`.

## Memory Ownership

- Inputs are owned by the host. The host must keep input buffers valid for the duration
  of the ABI call.
- Outputs are owned by native code. The host must call `n3_free` on any non-empty
  `n3_buffer` returned by the ABI.
- Hosts must not free ABI output buffers using any allocator other than `n3_free`.

## Concurrency

- Concurrency is not guaranteed by this contract.
- Hosts must serialize calls or provide external synchronization.

## Determinism

- Identical inputs produce identical outputs.
- No time, randomness, environment, filesystem, or network access is permitted.
- Outputs must be canonical bytes and must not contain host paths or secrets.

## Status Codes

The ABI uses stable status codes defined in `namel3ss_native.h`.
Hosts must treat non-OK status values as deterministic failures.

## Forbidden Behaviors

- Accessing host filesystem or network.
- Reading environment variables for behavior.
- Returning nondeterministic results.
- Replacing Python-defined semantics.

## Reference Assets

- ABI header: `native/include/namel3ss_native.h`
- C example: `examples/embed/c/main.c`
- C++ example: `examples/embed/cpp/main.cc`
- Rust example: `examples/embed/rust/main.rs`
