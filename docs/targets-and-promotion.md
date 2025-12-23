# Targets and promotion (Phase 5)

Targets describe how an app should run, using the same `.ai` file and capsules:

- `local` — dev mode (preferred persistence: SQLite).
- `service` — long-running server with `/health` and `/version` (preferred persistence: Postgres).
- `edge` — latency-sensitive, limited runtime (simulated stub in this alpha).

Targets are picked in the CLI, not inside `.ai`.

## Run

```
n3 run                     # auto-detects app.ai, target=local
n3 run app.ai              # file-first
n3 run --target service    # service runner (default port 8787, /health + /version)
n3 run --target edge       # edge simulator stub
```

## Build

```
n3 build --target service          # deterministic artifacts
n3 build app.ai --target local     # file-first
```

Artifacts live in `.namel3ss/build/<target>/<build-id>/` and include:
- program snapshot (`program/`),
- config snapshot (secrets redacted),
- lockfile snapshot,
- program summary,
- target bundle (service README with health endpoint info; edge stub README).

## Promote and rollback

```
n3 promote --to service      # promote the latest service build (or pass --build)
n3 status                    # show active target, build id, persistence target
n3 promote --rollback        # revert the active build pointer
```

Promotion updates pointers only; it’s safe and reversible. Database schema migrations are **not** auto-rolled back in this phase.

## Demo script

From a project folder:

```
n3 run
n3 build --target service
n3 promote --to service
n3 status
n3 promote --rollback
```

`service` target runs at `http://127.0.0.1:8787/health` (default). Edge target is a simulator stub until the full runtime lands.
