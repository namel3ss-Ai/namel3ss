# Building a RAG App with Patterns

This tutorial builds a deterministic RAG app using Phase 3 patterns and components.

## 1. Scaffold an app

```bash
n3 create rag_app support_assistant
```

This generates:

- `app.ai`
- `patterns/rag_chat.json`
- `docs/notes.md`

## 2. Enable capabilities

Your runtime must include:

- `ui.custom_layouts`
- `ui.rag_patterns`

Studio mode can render and debug without explicit capability import.

## 3. Use pattern state contracts

Main keys:

- `chatState.messages`
- `chatState.streaming`
- `chatState.citations`
- `chatState.selectedCitationId`
- `chatState.documents`
- `ingestionState.status`

Keep keys stable to preserve replay and snapshot determinism.

## 4. Wire actions

Required actions:

- `component.chat.send`
- `component.citation.open`
- `component.document.select`
- `component.ingestion.retry`

Action processing order is deterministic:

1. `order`
2. `line`
3. `column`
4. `id`

## 5. Add explain mode

`component.explain_mode` is Studio-only by default and should be enabled for debugging retrieval chunks, scores, and rerank details.

## 6. Validate and test

```bash
python -m compileall src -q
python -m pytest -q tests/patterns tests/components
python tools/line_limit_check.py
python tools/responsibility_check.py
```

## 7. Integration guidance

- Keep streaming updates serial (sorted event queue).
- Keep citation clicks idempotent.
- Keep ingestion retries explicit and user-triggered.
- Avoid hidden global UI state; always use declared state paths.
