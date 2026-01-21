# Targets and promotion

Targets describe how an app should run, using the same `.ai` file and module files:

- `local` — dev mode (preferred persistence: SQLite).
- `service` — long-running server with `/health` and `/version` (preferred persistence: Postgres).
- `edge` — latency-sensitive, limited engine (simulated stub).

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

Build artifacts are managed by namel3ss and include program/config snapshots,
lockfile snapshot, program summary, the UI intent, and the target bundle.
Artifacts are written to `.namel3ss/build/<target>/<build_id>/` and are deterministic (no timestamps).

Build output layout (stable):
- `build.json` — build metadata (intent only, no absolute paths).
- `manifest.json` — normalized UI intent (static).
- `ui/ui.json`, `ui/actions.json`, `ui/schema.json` — UI contract exports.
- `schema/records.json` — record schema snapshot (compatibility gate).
- `program/` — snapshot of the .ai sources used for the build.
- `config.json`, `lock_snapshot.json`, `program_summary.json` — build inputs summary.
- `entry.json` — entry instructions for the build.
- `web/` — production runtime assets for `n3 start`.
- `build_report.json`, `build_report.txt` — deterministic build report.
- `service/README.txt` or `edge/README.txt` — target bundle notes.
Use `n3 exists` to explain why a build exists and what changed.
For run diagnostics use `n3 status` and `n3 explain`. `n3 clean` removes runtime artifacts;
build outputs live in `.namel3ss/build/` and are safe to delete and recreate.

## Start (production)

```
n3 start --target service
```

`n3 start` serves the production UI from build artifacts. It does not include dev overlays,
watchers, or preview markers. It uses the service target and the latest build (or the promoted build if present).

## Promote and rollback (ship)

```
n3 ship --to service      # promote the latest service build (or pass --build)
n3 where                  # show active target, build id, persistence target
n3 ship --back            # revert the active build pointer (alias: --rollback)
```

Promotion updates pointers only; it’s safe and reversible. Database schema migrations are **not** auto-rolled back.

## Demo script

From a project folder:

```
n3 run
n3 pack --target service
n3 ship --to service
n3 start --target service
n3 where
n3 ship --back
```

`service` target runs at `http://127.0.0.1:8787/health` (default). Edge target is a simulator stub.

## Command map
- ship (alias: promote)
- pack (alias: build)
- start
- where
