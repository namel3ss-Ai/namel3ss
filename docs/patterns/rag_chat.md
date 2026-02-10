# RAG Chat Pattern

`rag_chat` is a deterministic three-pane pattern for retrieval-augmented chat:

- Left pane: `component.document_library`
- Center pane: `component.chat_thread` and sticky `component.ingestion_progress`
- Right pane: `component.citation_panel` and optional `component.explain_mode`

## Capability

Requires `ui.rag_patterns` in runtime mode.

- Runtime: capability required.
- Studio: capability optional for local debugging.

## Build API

```python
from namel3ss.ui.patterns.rag_chat import build_rag_chat_pattern

fragment = build_rag_chat_pattern(capabilities=("ui.rag_patterns",), studio_mode=False)
```

The returned fragment includes:

- `state`: stable state contract (`chatState.messages`, `chatState.citations`, `ingestionState.status`, ...)
- `layout`: deterministic three-pane structure
- `actions`: deterministic action IDs and ordering

## Determinism

- Stable IDs: derived from pattern name + node kind + declaration path.
- Action order: explicit `order` fields.
- Replay: same config yields byte-stable JSON after canonicalization.
- Concurrency: chat and ingestion events are processed serially in sorted event order.

## Validation

`validate_rag_chat_pattern` rejects invalid layouts, including `component.chat_thread` nodes outside `layout.main`.

## Runtime component contracts

- `component.chat_thread`
  - state: `chatState.messages`, `chatState.streaming`, `chatState.selectedCitationId`
  - actions: `component.chat.send`
- `component.citation_panel`
  - state: `chatState.citations`, `chatState.selectedCitationId`
  - actions: `component.citation.open`
- `component.document_library`
  - state: `chatState.documents`, `chatState.selectedDocumentId`
  - actions: `component.document.select`
- `component.ingestion_progress`
  - state: `ingestionState.status`
  - actions: `component.ingestion.retry`
- `component.explain_mode`
  - Studio-only by default (`studio_only: true`)
