# {{PROJECT_NAME}} (ClearOrders)

ClearOrders demo with sample orders, AI Q&A, and a why-it-matters panel.

Run it with:
- `n3 app.ai check`
- `n3 app.ai studio`
- `n3 app.ai actions`

## Secrets setup (optional)

This app may require secrets depending on providers/targets. Studio → Setup shows what’s missing.

Option A: local `.env`
1) Copy `.env.example` to `.env` next to `app.ai`.
2) Set the provider key you plan to use (preferred `NAMEL3SS_*`; aliases supported: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`/`GOOGLE_API_KEY`, `MISTRAL_API_KEY`).

Option B: shell export
- `export NAMEL3SS_OPENAI_API_KEY="your-key"`
- `export OPENAI_API_KEY="your-key"`

Verify:
- `n3 secrets status --json`

Default uses the mock assistant. If a key is present, the app auto-selects OpenAI when you run Ask AI or Draft reply.
