# Ingestion

Ingestion converts uploaded files into clean, deterministic text chunks that can be safely indexed and retrieved. The pipeline is explicit and does not use AI or probabilistic logic.

## What ingestion does
- Detects the upload type (`text`, `pdf`, `image`, `docx`) and basic traits (page count, embedded images).
- Extracts text deterministically for the detected type.
- Computes quality signals and applies a quality gate.
- Normalizes and chunks text for indexing when allowed.
- Captures page-level provenance for each chunk.

## Quality gate
Each upload produces exactly one status:
- `pass`: safe to index.
- `warn`: indexed, but marked `low_quality`.
- `block`: not indexed.

Gate decisions are based only on deterministic signals (no AI). The report is stored at:

```
state.ingestion[upload_id]
```

Report fields:
- `upload_id`
- `status`
- `method_used`
- `detected`
- `signals`
- `preview`
- `reasons`
- `provenance`

Provenance fields:
- `document_id`
- `source_name`

Chunk entries live in:

```
state.index.chunks
```

Chunk fields:
- `upload_id`
- `document_id`
- `source_name`
- `page_number`
- `chunk_index`
- `chunk_id`
- `order`
- `text`
- `chars`
- `low_quality`

## Running ingestion
Ingestion runs through a deterministic UI action:

```
ingestion_run { upload_id, mode? }
```

Modes:
- `primary` (default)
- `layout` (PDF layout extraction)
- `ocr` (image OCR extraction)

Use the upload checksum from `state.uploads` as `upload_id`.

## Indexing policy
- `pass`: chunks indexed.
- `warn`: chunks indexed with `low_quality: true`.
- `block`: no chunks or index entries.

Blocked content is never retrievable.

## Retrieval safety
Retrieval uses the ingestion report to prefer `pass` content, include `warn` only when policy allows it, and always exclude `block`.

## Review and corrective actions
Ingestion reports are inspectable and read-only until a user takes an explicit action. Actions are deterministic and must be invoked deliberately:

- `ingestion_review { upload_id? }` to list reports (optional filter).
- `ingestion_run { upload_id, mode: primary | layout | ocr }` to re-run extraction.
- `ingestion_skip { upload_id }` to explicitly exclude a warn/block upload from indexing.
- `upload_replace { upload_id }` as a placeholder to signal a replacement is needed.

No ingestion retries or overrides happen automatically. Indexing only changes when an explicit action is executed.

## Policy and permissions
Ingestion actions are gated by a declarative policy block in `app.ai`:

```
policy
  allow ingestion.run
  allow ingestion.review
  require ingestion.override with ingestion.override
  require ingestion.skip with ingestion.skip
  require retrieval.include_warn with retrieval.include_warn
  require upload.replace with upload.replace
```

Rules are `allow`, `deny`, or `require` (with explicit permission names). Order is irrelevant and no expressions are allowed.

If the policy block is omitted, defaults apply: `ingestion_run` and `ingestion_review` are allowed, while overrides, skips, warned retrieval, and upload replacement require explicit permissions. Denied actions return a policy error and perform no state changes.

Blocked content is never retrievable, regardless of policy.

The legacy `ingestion.policy.toml` file is still supported; app policy overrides it only for actions explicitly declared in the policy block.

## Explain audit
Use audit explain to reconstruct upload selection, the quality gate, review actions, and policy decisions without reading code:

```
n3 explain --audit --input .namel3ss/run/last.json --upload <checksum>
```

Audit output is deterministic, ordered, and redacted. It does not allow silent indexing or hidden overrides.
