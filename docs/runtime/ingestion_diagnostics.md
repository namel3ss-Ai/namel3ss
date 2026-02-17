# Ingestion Diagnostics

Ingestion diagnostics provide deterministic reason codes, messages, and remediation hints for blocked and warned uploads.

## Report contract
When `ingestion.enable_diagnostics = true`, each ingestion report can include:

- `reasons`: deterministic ordered reason codes.
- `reason_details`: ordered objects with:
  - `code`
  - `message`
  - `remediation`

Ordering is stable:

1. Probe reasons (`PROBE_REASON_ORDER`)
2. Quality reasons (`QUALITY_REASON_ORDER`)
3. Additional reasons (for example `ocr_failed`)

## OCR fallback behavior
When `ingestion.enable_ocr_fallback = true` and ingestion is running in `primary` mode:

1. Primary extraction runs.
2. Quality gate runs.
3. If status is `block`, detected type is `pdf`, and reasons include one of:
   - `text_too_short`
   - `empty_text`
   - `low_unique_tokens`
4. OCR fallback runs once.

Outcomes:

- Fallback success (`pass` or `warn` quality) forces final status to `warn`, sets `fallback_used = "ocr"`, and indexing proceeds.
- Fallback failure keeps status `block`, sets `fallback_used = "ocr"`, and adds `ocr_failed`.

## Canonical reason mapping

| Code | Message | Remediation |
| --- | --- | --- |
| `empty_content` | The upload is empty. | Upload a file that contains content. |
| `null_bytes` | Null bytes were detected in the upload. | Upload a text-based file or convert the document to UTF-8 text. |
| `size_limit` | The upload is too large for ingestion limits. | Split the document into smaller files and upload again. |
| `utf8_invalid` | The upload has invalid UTF-8 byte sequences. | Convert the file to valid UTF-8 text before uploading. |
| `binary_markers` | Binary markers were detected in text content. | Upload plain text or use a supported document format. |
| `pdf_missing_eof` | The PDF appears truncated or missing EOF markers. | Regenerate the PDF and upload a complete file. |
| `text_too_short` | Extracted text is too short for reliable indexing. | Upload a fuller text document or run OCR for scanned PDFs. |
| `low_unique_tokens` | Low number of unique tokens; content may be repetitive. | Upload a clearer source file with richer text content. |
| `high_non_ascii` | A high share of non-ASCII characters was detected. | Check text encoding and upload a normalized UTF-8 document. |
| `repeated_lines` | Many lines are repeated. | Remove duplicated sections and upload a cleaner document. |
| `table_heavy` | Content is heavily table-like and may chunk poorly. | Convert critical tables to readable prose or CSV with context. |
| `many_empty_pages` | Many pages are empty after extraction. | Remove blank pages or upload a text-based source file. |
| `empty_text` | No extractable text was found. | Run OCR or upload a PDF with embedded text. |
| `ocr_failed` | OCR fallback failed; provide a text-based PDF. | Upload a PDF with embedded text or reinstall `namel3ss` to restore bundled OCR runtime files. |
| `skipped` | Ingestion was skipped for this upload. | Run ingestion again or replace the upload with a better source file. |

Unknown codes are rendered with generic guidance so diagnostics remain stable even when new codes are introduced.
