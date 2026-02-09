# App Packaging

`app.n3a` is the canonical namel3ss app artifact.

## Archive contents

Each archive contains deterministic JSON files:

- `app_descriptor.json`
- `compiled_ir.json`
- `ui_manifest.json`
- `permissions.json`
- `ui_state_schema.json`
- `runtime_config.json`
- `static_assets.json`

## Determinism

- Archive entries are sorted by path.
- Zip timestamps are fixed.
- JSON payloads use canonical key ordering.
- Same source produces byte-identical output.

## Runtime contract

- `namel3ss run` validates `.n3a` before execution.
- Invalid archive files are rejected with deterministic errors.
- Archives built with newer namel3ss versions are rejected.
- Permission declarations are validated before run.

## Commands

```bash
namel3ss build app.ai
namel3ss inspect app.n3a
namel3ss run app.n3a
```
