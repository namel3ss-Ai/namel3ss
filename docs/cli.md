# CLI

The app packaging CLI is intentionally short.

## Build

```bash
namel3ss build app.ai
```

This writes `app.n3a` beside `app.ai`.

Optional output path:

```bash
namel3ss build app.ai --out myapp.n3a
```

## Run

```bash
namel3ss run app.n3a
```

This runs in production mode by default.

Studio mode is positional:

```bash
namel3ss run app.n3a studio
```

## Inspect

```bash
namel3ss inspect app.n3a
```

The output is deterministic JSON with app metadata, permissions, pages, ui_state, capabilities, and checksum.
