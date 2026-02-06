# Cross-Language Compilation

namel3ss can compile a pure flow into deterministic C, Rust, or WebAssembly project outputs.

## Commands

```bash
n3 compile --lang c --flow add --out dist
n3 compile --lang rust --flow add --out dist
n3 compile --lang wasm --flow add --out dist
n3 compile list
n3 compile clean --out dist
n3 wasm run dist/add/wasm/target/wasm32-wasip1/release/flow_runner.wasm --input '{"a":2,"b":3}'
```

## Config

Use `compilation.yaml` to track target choices per flow.

```yaml
flows:
  add: rust
  score: wasm
```

## ABI

Generated C and Rust projects export:

- `int run_flow(const char *input_json, char **output_json, char **error_json)`
- `void free_json_string(char *ptr)`

The output and error payloads are deterministic JSON strings.

## Current Limits

This phase compiles numeric pure flows only.

- Flow must be declared `purity is "pure"`.
- Supported statements: `let`, `return`.
- Supported expressions: numeric literals, `input.<field>`, local refs, unary `+`/`-`, binary `+ - * / %`.

Unsupported patterns fail with explicit guidance instead of falling back silently.

## Determinism

- Generated file ordering is stable.
- Generated code content is stable for the same source flow.
- `compiled_module.json` is written with canonical key order.
