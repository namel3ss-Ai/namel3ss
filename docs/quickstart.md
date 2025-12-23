# namel3ss Quickstart

Run any `.ai` app with the file-first CLI.

## Troubleshooting first

- If something doesn’t run, start with `n3 doctor` (use `--json` for scripts/CI).

## Create a project

- Scaffold: `n3 new <template> [project_name]` (templates: `crud`, `ai-assistant`, `multi-agent`)
- Example: `n3 new crud my_app` then `cd my_app`
- The app file lives at `app.ai`; commands below assume you are in the project directory.
- Multi-file apps use modules under `modules/<name>/capsule.ai`.

## Core commands

- Validate: `n3 app.ai check`
- UI manifest: `n3 app.ai ui`
- Actions list: `n3 app.ai actions`
- Studio (local viewer/interactor): `n3 app.ai studio`
- Run default flow (when only one flow): `n3 app.ai`
- Run specific flow (CRUD template): `n3 app.ai flow "seed_customers"`
- Run an action (CRUD template): `n3 app.ai page.home.form.customer '{"values":{"name":"Ada","email":"ada@example.com","age":23}}'`
- Run tests: `n3 test`

Formatter and linter:

- Format: `n3 app.ai format`
- Format check (CI): `n3 app.ai format check`
- Lint: `n3 app.ai lint`
- Lint check (CI): `n3 app.ai lint check`

## Demos

Bundled demos under `examples/` you can run immediately:

- CRUD Dashboard: `n3 examples/demo_crud_dashboard.ai studio`
- Onboarding flow: `n3 examples/demo_onboarding_flow.ai studio`
- AI assistant over records: `n3 examples/demo_ai_assistant_over_records.ai studio`

## Studio tips

- `Refresh` reloads manifest, actions, lint.
- `Reset` clears state/store (warns before clearing persisted data when SQLite is enabled).
- Actions run via buttons and forms; traces and state update live.

## Persistence (opt-in)

- Set `N3_PERSIST=1` to persist locally to `.namel3ss/data.db` instead of memory.
- Check status: `n3 app.ai persist status`.
- Reset persisted data: `n3 app.ai persist reset --yes` (confirmation required, SQLite only).

## Grammar note
- Record fields use `is` for types and `must` for constraints, and canonical types are `text`, `number`, `boolean`, for example: `field "email" is text must be present`, `field "age" is number must be greater than 17`, `field "active" is boolean must be present`.

## Next steps
- Read [First 5 minutes](first-5-minutes.md) for a guided win.
- Run the [CRUD dashboard example](examples/demo_crud_dashboard.ai) after your first project.
- See [What you can build today](what-you-can-build-today.md) to understand supported use cases.
- Learn expressions and conditionals in [Expressions & Conditionals](expressions-and-conditionals.md).
- Learn Capsules + tests in [Modules and Tests](modules-and-tests.md).
- UI details live in the [UI DSL Spec](ui-dsl.md).

## Form payloads (CLI)

- Canonical: `{"values":{"email":"ada@example.com","name":"Ada"}}`
- Also accepted (auto-wrapped): `{"email":"ada@example.com","name":"Ada"}` — prefer the canonical shape in docs/scripts.
