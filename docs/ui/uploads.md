# Upload UX contract

## Scope
This document defines the upload UX lifecycle, required states, and explain visibility.

## Lifecycle and states
- Uploads are request-only UI elements; selection does not imply ingestion.
- The manifest includes deterministic upload requests (`upload_requests`) with `name`, `accept`, `multiple`, `required`, `label`, and `preview`.
- Selection updates `state.uploads.<name>` as a map keyed by file id/checksum:
  - `{ "<id>": {"id","name","size","type","checksum"} }`
- Ingestion is explicit and separate, triggered only by ingestion actions.
- `multiple: false` replaces the existing file; `multiple: true` appends deterministically by selection order.
- `required: true` gates flow execution when the target flow reads `state.uploads.<name>`.

## Progress semantics
- Progress is a runtime-owned surface with deterministic state transitions.
- Progress reporting is bounded to upload selection and ingestion actions.
- UI does not declare custom progress behaviors.

## Preview metadata
- Preview metadata is derived from selection only.
- Metadata is limited to file identity fields (`id`, `name`, `size`, `type`, `checksum`) plus bounded preview summaries.
- No raw content is surfaced in manifests or explain output.

## Error states and recovery
- Upload selection and ingestion errors are surfaced as explicit UX states.
- Errors are explainable and deterministic; no implicit retries or background recovery.
- Recovery is explicit via user-triggered actions.

## Explain and Studio visibility
- Explain output includes upload actions and their availability.
- Studio surfaces upload selection metadata and error states without exposing raw content.
- Studio/dev can inject a minimal upload control when uploads capability is enabled and no upload control is declared.
- Production never auto-injects upload controls; warnings surface misconfiguration instead.
