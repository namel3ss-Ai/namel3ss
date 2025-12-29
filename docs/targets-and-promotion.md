# Targets and promotion (Phase 5)

Targets describe how an app should run, using the same `.ai` file and module files:

- `local` — dev mode (preferred persistence: SQLite).
- `service` — long-running server with `/health` and `/version` (preferred persistence: Postgres).
- `edge` — latency-sensitive, limited engine (simulated stub in this alpha).

Targets are picked in the CLI, not inside `.ai`.

## Run

```
n3 run                     # auto-detects app.ai, target=local
n3 run app.ai              # file-first
n3 run --target service    # service runner (default port 8787, /health + /version)
n3 run --target edge       # edge simulator stub
```

## Build (pack)

```
n3 pack --target service          # deterministic artifacts (alias: build)
n3 pack app.ai --target local     # file-first
```

Artifacts live in `.namel3ss/build/<target>/<build-id>/` and include:
- program snapshot (`program/`),
- config snapshot (secrets redacted),
- lockfile snapshot,
- program summary,
- target bundle (service README with health endpoint info; edge stub README).

Build manifests live in `.namel3ss/build/last.json` and history under `.namel3ss/build/history/`.
Use `n3 exists` to explain why a build exists and what changed.

## Promote and rollback (ship)

```
n3 ship --to service      # promote the latest service build (or pass --build)
n3 where                  # show active target, build id, persistence target (alias: status)
n3 ship --back            # revert the active build pointer (alias: --rollback)
```

Promotion updates pointers only; it’s safe and reversible. Database schema migrations are **not** auto-rolled back in this phase.

## Demo script

From a project folder:

```
n3 run
n3 pack --target service
n3 ship --to service
n3 where
n3 ship --back
```

`service` target runs at `http://127.0.0.1:8787/health` (default). Edge target is a simulator stub until the full engine lands.

## Command map
- ship (alias: promote)
- pack (alias: build)
- where (alias: status)
