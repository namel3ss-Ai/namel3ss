# Ingestion Dashboard Pattern

`ingestion_dashboard` is a deterministic two-pane pattern:

- Primary pane: `component.document_library`
- Secondary pane: `component.ingestion_progress`

## Capability

Requires `ui.rag_patterns` in runtime mode.

## Build API

```python
from namel3ss.ui.patterns.ingestion_dashboard import build_ingestion_dashboard_pattern

fragment = build_ingestion_dashboard_pattern(capabilities=("ui.rag_patterns",), studio_mode=False)
```

## State contract

- `ingestionState.documents`: list of documents
- `ingestionState.selectedDocumentId`: selected document id
- `ingestionState.status`: status payload (`status`, `percent`)
- `ingestionState.errors`: ingestion error messages

## Determinism

- IDs are generated from deterministic hashes.
- Action ordering is explicit and stable.
- Validation is deterministic and reports explicit errors.

## Validation rules

`validate_ingestion_dashboard_pattern` enforces:

- `component.document_library` exists in primary pane
- `component.ingestion_progress` exists in secondary pane
