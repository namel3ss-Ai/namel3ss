# What you can build today

- CRUD dashboards with forms + tables backed by in-memory or SQLite persistence (`N3_PERSIST=1`).
- AI-assisted UIs that call flows and render traces alongside state.
- Simple onboarding flows with buttons/forms calling deterministic logic (no conditionals required).
- Multi-agent workflows using the provided `ai` + `agent` primitives and tool-call traces.
- Internal tools that capture inputs via forms and fan out to flows or record saves.

See `examples/` for runnable demos and start with `n3 doctor` if setup fails. Keep payloads in the canonical `{"values": {...}}` shape for scripts, even though flat objects are auto-wrapped.
