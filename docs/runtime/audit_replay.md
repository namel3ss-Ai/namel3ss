# Audit Artifacts & Replay

Namel3ss can emit deterministic, immutable run artifacts under `.namel3ss/audit/` and replay them with a stable verifier.

## Policy modes

Configure audit behavior in `namel3ss.toml`:

```toml
[audit]
mode = "optional" # required | optional | forbidden
```

Environment override:

```bash
N3_AUDIT_POLICY=required
```

Mode behavior:
- `required`: runtime must write an audit bundle; write failures become structured runtime errors.
- `optional`: runtime writes bundles best-effort.
- `forbidden`: runtime does not write bundles.

## Artifact layout

Per run:
- `.namel3ss/audit/<run_id>/run_artifact.json`
- `.namel3ss/audit/<run_id>/bundle.json`

Latest pointers:
- `.namel3ss/audit/last/run_artifact.json`
- `.namel3ss/audit/last/bundle.json`

`bundle.json` contains:
- `schema_version`
- `run_id`
- `integrity_hash`
- `run_artifact_path`
- `bundle_path`

## Replay

Legacy explain replay still works:

```bash
n3 replay app.ai
n3 replay --log .namel3ss/explain/last_explain.json --json
```

Run artifact replay:

```bash
n3 replay --artifact .namel3ss/audit/last/run_artifact.json --json
```

Replay verifies deterministic checksums and reports explicit mismatches (`run_id`, `checksums.*`).

