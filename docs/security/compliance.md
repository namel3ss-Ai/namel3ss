# Compliance

Compliance artifacts are first-class, deterministic, and repo-owned.

## Artifacts
- LICENSE (root)
- NOTICE (root)
- docs/security/compliance.md

## Attribution inventory
Declared dependencies are listed in NOTICE with stable ordering and no version numbers.

## License consistency
- pyproject.toml declares license file as LICENSE.
- LICENSE must exist at repo root.

## Determinism
- Compliance artifacts avoid timestamps and environment-specific data.
