# Versioning, Quality, and MLOps

This phase adds version metadata, deprecation warnings, quality gates, and model registry hooks.

## Files

- `versions.yaml`: route, flow, and model version lifecycle metadata.
- `quality.yaml`: naming, schema, and prompt bias rules.
- `mlops.yaml`: model registry endpoint and project name.

## Versioning

Use `kind:name` for entities:

- `route:list_users`
- `flow:summarise`
- `model:base`

Commands:

- `n3 version list --json`
- `n3 version add route:list_users 2.0 --target list_users_v2_route --status active`
- `n3 version deprecate route:list_users 1.0 --replacement 2.0 --eol 2026-06-01`
- `n3 version remove route:list_users 0.9`

Routing behavior:

- `Accept-Version` header or `?version=` query picks an exact version.
- If no exact version is found, runtime falls back to the latest live version.
- Deprecated calls return `X-N3-Deprecation-Warning`.
- Removed versions return `404` with a deprecation warning header.

## Quality Gates

Run quality checks:

- `n3 quality check --json`
- `n3 quality fix --json`

Quality checks include:

- Snake case naming.
- Reserved word avoidance.
- Typed schema fields.
- Maximum field length.
- Prompt/system-text disallowed words.

Example `quality.yaml`:

```yaml
naming:
  enforce_snake_case: true
schema:
  max_field_length: 64
  required_fields:
    - id
prompts:
  disallow_words:
    - unsafe
    - secret
```

`n3 marketplace publish` and `n3 mlops register-model` enforce quality gates.

## MLOps

Configure `mlops.yaml`:

```yaml
registry_url: file://./.namel3ss/registry_ops.json
project_name: demo_app
```

Commands:

- `n3 mlops register-model base 1.0 --artifact-uri model://base/1.0 --metric accuracy=0.91 --json`
- `n3 mlops get-model base 1.0 --json`

Offline behavior:

- Failed registry calls are queued in `.namel3ss/mlops_cache.json`.
- Local registry snapshot is stored in `.namel3ss/mlops_registry.json`.
- Retrain scheduling attempts to create experiment entries when MLOps is configured.

## Studio Panels

Studio now includes menu actions for:

- Versioning
- Quality
- MLOps

The panels call `/api/versioning`, `/api/quality`, and `/api/mlops`.
