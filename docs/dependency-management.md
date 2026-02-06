# Unified Dependency Management

namel3ss now supports one manifest for pack, python, and system dependencies.

## Capability Gate

Enable `dependency_management` in your app to use the unified commands:

```ai
spec is "1.0"

capabilities:
  dependency_management
```

## Manifest

Declare dependencies in `namel3ss.toml`:

```toml
[dependencies]
huggingface = "github:namel3ss/huggingface-pack@v0.3.0"

[runtime.dependencies]
python = [
  "requests==2.31.0",
  "torch>=2.0,<3.0",
]
system = [
  "postgresql-client@13",
]
```

## Lockfiles

`n3 install` writes deterministic lockfiles:

- `namel3ss.lock` (primary)
- `namel3ss.lock.json` (compatibility alias)
- `requirements.lock.txt` (python environment snapshot when python runtime deps are installed)

The lockfile records resolved packs plus runtime dependency entries with checksum, source, and trust metadata.

- Python runtime entries use artifact checksums when a local `.venv` is installed (derived from installed wheel metadata).
- System runtime entries use artifact checksums when package-manager metadata is available; otherwise they fall back to deterministic spec checksums.

## CLI

Core commands:

- `n3 install`
- `n3 update`
- `n3 tree`
- `n3 deps add <library@version>`
- `n3 deps add --system <package@version>`
- `n3 deps remove <library==version>`
- `n3 deps remove --system <package@version>`
- `n3 deps status`
- `n3 deps verify`
- `n3 deps audit`
- `n3 deps clean`

Use `--json` for machine-readable output.

## Determinism and Security

- The same `namel3ss.toml` and lockfile produce the same dependency graph.
- Lockfile writes are canonical and sorted.
- Runtime dependency checksums prefer local artifact metadata and are verified by `n3 deps verify`.
- `n3 deps audit` surfaces known advisories and trust-tier warnings.
- No post-install hooks or arbitrary scripts are executed by dependency operations.

## Studio

Studio Setup now includes a Dependencies section backed by `/api/dependencies`.
It shows counts, lockfile status, a searchable dependency graph, runtime dependency remove controls, and install/update actions.
