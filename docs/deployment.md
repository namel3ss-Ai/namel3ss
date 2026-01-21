# Packaging and Deployment

namel3ss packaging and deployment are deterministic and explicit. Build artifacts never include secrets or host paths, and shipping only updates pointers.

## Build outputs

`n3 pack` writes deterministic artifacts under:

```
.namel3ss/build/<target>/<build_id>/
```

Each build includes:
- Program snapshot under `program/`
- Redacted config summary in `config.json`
- Target info and entry instructions in `build.json` and `entry.json`
- UI contract under `ui/`
- Schema snapshot under `schema/`
- Runtime assets under `web/`
- Build report under `build_report.json` and `build_report.txt`

Build outputs are safe to delete and recreate. Re-running `n3 pack` with the same inputs produces the same build id.

## Pack vs ship

- `n3 pack` creates build artifacts. It does not change which build is active.
- `n3 ship` promotes a build to a target. It only updates pointers.
- `n3 ship --back` rolls back to the previous promoted build.

Shipping never auto-upgrades builds. Use `--build` to pick a specific build id.

## Environment configuration

Configuration sources are explicit:
- `namel3ss.toml`
- `.env`
- environment variables

Required variables depend on your app:
- Provider keys (for example `NAMEL3SS_OPENAI_API_KEY`)
- Persistence URLs (`N3_DATABASE_URL` or `N3_EDGE_KV_URL`)
- Custom secrets (`N3_SECRET_<NAME>`)

Optional variables can override config (for example `N3_PERSIST_TARGET`, `N3_DB_PATH`, `N3_TOOL_SERVICE_URL`).
Studio and `/api/deploy` show a redacted environment summary with required vs optional keys and guidance.

## Targets

Targets are explicit and chosen in the CLI:

- `local` for development
- `service` for long-running deployments
- `edge` for the edge simulator

Use `n3 start --target service` to serve the production UI from build artifacts.

## Safe rollback

Rolling back updates the active build pointer only. Data migrations are not automatically rolled back.

## Common mistakes

- Running `n3 start` without a service build
- Shipping a build for the wrong target
- Missing required environment variables
- Editing build artifacts instead of rebuilding

## Studio and API

Studio includes a Deploy panel that shows:
- Active build and target
- Last ship action
- Deployment status and guidance
- Environment summary

Runtime APIs:
- `GET /api/build` for build metadata
- `GET /api/deploy` for deployment state and environment summary
