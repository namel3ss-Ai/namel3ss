# Retrieval

Retrieval returns ingested text chunks in a deterministic, quality-aware order. It never returns blocked content.

## Quality-aware ordering
- `pass`: returned first.
- `warn`: returned only when no `pass` results exist and policy allows warned retrieval.
- `block`: never returned.

Retrieval decisions are based only on ingestion reports stored under:

```
state.ingestion[upload_id]
```

## Retrieval action
Retrieval runs through a deterministic UI action:

```
retrieval_run { query, limit? }
```

Results include:
- `upload_id`
- `chunk_id`
- `quality` (`pass` or `warn`)
- `low_quality` (true when quality is `warn`)

Blocked content is always excluded, even if it is the only match. Warned content is excluded unless `retrieval.include_warn` is allowed by policy.

Retrieval reflects the latest ingestion report; re-running ingestion or skipping an upload immediately updates what can be returned.

Warned retrieval permissions can be declared in the `policy` block of `app.ai` (legacy `ingestion.policy.toml` is still supported).

## Explain audit
Audit explain shows why each upload was included or excluded for a given query, including policy involvement:

```
n3 explain --audit --input .namel3ss/run/last.json --query "invoice"
```

Blocked uploads are always excluded and appear in the audit report with explicit reasons.
