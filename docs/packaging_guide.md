# Packaging Guide

## Build
Use:

```bash
n3 build app.ai --out dist --target service
```

Optional profiling:

```bash
n3 build app.ai --out dist --target service --profile --profile-iterations 3
```

Build output includes:
- `manifest.json`
- `package_manifest.json`
- `assets/` (themes, i18n bundles, plugins)
- `performance_profile.json` (when profiling is enabled)
- deterministic archive: `*.n3bundle.zip`

## Deploy
Use:

```bash
n3 deploy dist/app_service.n3bundle.zip --out deploy --channel filesystem
```

Multiple channels:

```bash
n3 deploy dist/app_service.n3bundle.zip --channel filesystem,npm
```

Deploy output includes:
- channel-staged archives under `deploy/<channel>/`
- deterministic `deploy_report.json`

## Version Metadata
- Build metadata uses semantic version text from the installed `namel3ss` package.
- Fallback version is `0.0.0-dev` when package metadata is unavailable.

## Determinism Rules
- Archive entries are lexicographically ordered.
- Archive timestamps are fixed by the archive writer.
- Manifest and report JSON use canonical key ordering.
