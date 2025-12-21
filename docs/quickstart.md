# namel3ss Quickstart

Run any `.ai` app with the file-first CLI.

## Create a project

- Scaffold: `n3 new <template> [project_name]` (templates: `crud`, `ai-assistant`, `multi-agent`)
- Example: `n3 new crud my_app` then `cd my_app`
- The app file lives at `app.ai`; commands below assume you are in the project directory.

## Core commands

- Validate: `n3 app.ai check`
- UI manifest: `n3 app.ai ui`
- Actions list: `n3 app.ai actions`
- Studio (local viewer/interactor): `n3 app.ai studio`
- Run default flow (when only one flow): `n3 app.ai`
- Run specific flow (CRUD template): `n3 app.ai flow "seed_customers"`
- Run an action (CRUD template): `n3 app.ai page.home.form.customer '{"values":{"name":"Ada","email":"ada@example.com","age":23}}'`

Formatter and linter:

- Format: `n3 app.ai format`
- Format check (CI): `n3 app.ai format check`
- Lint: `n3 app.ai lint`
- Lint check (CI): `n3 app.ai lint check`

## Demos

Bundled demos remain under `examples/` if you want to inspect them directly:

- CRUD Dashboard: `n3 examples/demo_crud_dashboard.ai actions`
- AI Assistant over Records: `n3 examples/demo_ai_assistant_over_records.ai ui`
- Multi-Agent Workflow: `n3 examples/demo_multi_agent_workflow.ai studio`

## Studio tips

- `Refresh` reloads manifest, actions, lint.
- `Reset` clears in-memory state/store.
- Actions run via buttons and forms; traces and state update live.

## Grammar note
- Record fields use `is` for types and `must` for constraints, for example: `field "email" is text must be present`.

## Next steps
- Read [First 5 minutes](first-5-minutes.md) for a guided win.
- See [What you can build today](what-you-can-build-today.md) to understand supported use cases.
