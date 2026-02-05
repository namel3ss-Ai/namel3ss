# Plugin Protocol

Plugins let you run custom code in a separate process while keeping the core runtime stable.

## What a plugin receives

The plugin reads JSON from standard input.

Fields in the input payload:
- `inputs` is a map of input values for the flow.
- `state` is a map of the current state.
- `identity` is a map with identity data, when available.

`input` is accepted as a legacy alias for `inputs`.

## What a plugin returns

The plugin writes JSON to standard output.

Fields in the output payload:
- `ok` is true or false.
- `result` is a map when `ok` is true.
- `error` is a map with `type` and `message` when `ok` is false.

## Scaffold a plugin

Use the CLI to create a starter project:
- `n3 plugin new node demo_plugin`
- `n3 plugin new go demo_plugin`
- `n3 plugin new rust demo_plugin`

## Run a plugin in the sandbox

Add a command entry to `.namel3ss/sandbox.yaml`:

```
sandboxes:
  summarize:
    command: "node index.js"
```

The command should read the JSON payload from standard input and print a JSON response.
