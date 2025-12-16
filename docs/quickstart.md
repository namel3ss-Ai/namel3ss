# Namel3ss Quickstart

Run any `.ai` app with the file-first CLI. The examples live in `examples/`.

## Core commands

- Validate: `n3 examples/demo_crud_dashboard.ai check`
- UI manifest: `n3 examples/demo_crud_dashboard.ai ui`
- Actions list: `n3 examples/demo_crud_dashboard.ai actions`
- Studio (local viewer/interactor): `n3 examples/demo_crud_dashboard.ai studio`
- Run default flow (when only one flow): `n3 examples/demo_crud_dashboard.ai`
- Run specific flow: `n3 examples/demo_crud_dashboard.ai flow "seed_customers"`
- Run an action: `n3 examples/demo_crud_dashboard.ai page.home.form.customer '{"values":{"name":"Ada","email":"ada@example.com","age":23}}'`

Formatter and linter:

- Format: `n3 examples/demo_crud_dashboard.ai format`
- Format check (CI): `n3 examples/demo_crud_dashboard.ai format check`
- Lint: `n3 examples/demo_crud_dashboard.ai lint`
- Lint check (CI): `n3 examples/demo_crud_dashboard.ai lint check`

## Demos

### CRUD Dashboard
- File: `examples/demo_crud_dashboard.ai`
- Try: `n3 examples/demo_crud_dashboard.ai actions` to see `page.home.form.customer` and `page.home.button.seed_demo_data`.
- Seed data: `n3 examples/demo_crud_dashboard.ai page.home.button.seed_demo_data {}`
- Submit form: `n3 examples/demo_crud_dashboard.ai page.home.form.customer '{"values":{"name":"Ada","email":"ada@example.com","age":23}}'`

### AI Assistant over Records
- File: `examples/demo_ai_assistant_over_records.ai`
- Ask assistant: `n3 examples/demo_ai_assistant_over_records.ai page.notes.button.ask_assistant {}`
- Submit a note first: `n3 examples/demo_ai_assistant_over_records.ai page.notes.form.note '{"values":{"title":"Note 1","body":"Content"}}'`
- View UI: `n3 examples/demo_ai_assistant_over_records.ai ui`

### Multi-Agent Workflow
- File: `examples/demo_multi_agent_workflow.ai`
- Run workflow: `n3 examples/demo_multi_agent_workflow.ai page.workflow.button.run_workflow {}`
- Observe traces and state in Studio: `n3 examples/demo_multi_agent_workflow.ai studio`

## Studio tips

- `Refresh` reloads manifest, actions, lint.
- `Reset` clears in-memory state/store.
- Actions run via buttons and forms; traces and state update live.
