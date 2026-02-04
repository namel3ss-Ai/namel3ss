# What you can build today

- CRUD dashboards with forms + tables backed by in-memory or SQLite persistence (`N3_PERSIST=1`).
- Agent Lab dashboards that run agents, show Timeline explainability, and surface memory packs and handoffs.
- AI-assisted UIs that call flows and render traces alongside state.
- Auditable RAG knowledge bases with deterministic ingestion, retrieval, citations, preview, highlighting, and explain mode.
- Simple onboarding flows with buttons/forms calling deterministic logic (no conditionals required).
- Multi-agent workflows with explicit merge policies and deterministic tool-call traces.
- Internal tools that capture inputs via forms and fan out to flows or record saves.

Start with `n3 new operations_dashboard`, `n3 new onboarding`, or `n3 new support_inbox` and run `n3 doctor` if setup fails. Keep payloads in the canonical `{"values": {...}}` shape for scripts, even though flat objects are auto-wrapped.
