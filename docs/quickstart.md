# namel3ss Quickstart

Run any `.ai` app with the file-first CLI.

## Troubleshooting first

- If something doesn't run, start with `n3 doctor` (use `--json` for scripts/CI).

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
- Why mode: `n3 why` or `n3 explain --why`
- How mode: `n3 how`
- With mode: `n3 with`
- What mode: `n3 what`
- See mode: `n3 see`
- Fix mode: `n3 fix`
- Exists mode: `n3 exists app.ai`
- When mode: `n3 when app.ai`
- Memory recall: `n3 memory "hello"` (run from a folder with `app.ai`)
- Memory explain: `n3 memory why`
- Memory show: `n3 memory show`
- Memory with selector: `n3 memory @assistant "hello"`
- Pattern list: `n3 pattern list`
- Scaffold a pattern: `n3 pattern new admin-dashboard my_admin`
- Search packages: `n3 pkg search auth`
- Package info: `n3 pkg info auth-basic`
- Add a package: `n3 pkg add github:owner/repo@v0.1.0`
- Install packages: `n3 pkg install`
- Scaffold a package: `n3 new pkg my_capsule`
- Adoption kit: `n3 kit --format md`

Formatter and linter:

- Format: `n3 app.ai format`
- Format check (CI): `n3 app.ai format check`
- Lint: `n3 app.ai lint`
- Lint check (CI): `n3 app.ai lint check`

Try this:
- Run `n3 run app.ai`, then `n3 how`, `n3 with`, `n3 what`, and `n3 see`.
- Run a flow, then run `n3 what`.
- Run a tool example, then run `n3 with`.
- Try `n3 exists app.ai`.
- Run `n3 when app.ai` before running flows.
- Run a failing example then `n3 fix`.
- If something fails, try: `n3 fix`.

Memory proof harness (dev):
- Generate goldens: `python3 tools/memory_proof_generate.py`
- Check goldens: `python3 tools/memory_proof_check.py`

## Python tools

- Add Python code in `tools/*.py`.
- Declare the tool in `app.ai` with `implemented using python` plus `input`/`output` blocks.
- Bind the tool with `n3 tools bind --auto` (or `n3 tools bind "<name>" --entry ...`) or use **Tool Wizard**.
- Add dependencies in `pyproject.toml` or `requirements.txt`.
- Install deps: `n3 deps install`
- Run your flow: `n3 app.ai run` or `n3 app.ai studio`

**Tool Wizard 60-second path**
1) `n3 app.ai studio`
2) Click **Tool Wizard** -> fill fields -> Generate (writes `tools/*.py`, `app.ai`, `.namel3ss/tools.yaml`)
3) Run the flow in Studio or via `n3 app.ai run`

## Demos

Bundled demos under `examples/` you can run immediately:

- CRUD Dashboard: `n3 examples/demo_crud_dashboard.ai studio`
- Onboarding flow: `n3 examples/demo_onboarding_flow.ai studio`
- AI assistant over records: `n3 examples/demo_ai_assistant_over_records.ai studio`

## Studio tips

- `Refresh` reloads manifest, actions, lint.
- `Reset` clears state/store (warns before clearing persisted data when SQLite is enabled).
- Actions run via buttons and forms; traces and state update live.

## Persistence (dev/prod)

- Local dev uses SQLite by default (set `N3_PERSIST_TARGET=sqlite` in `.env` for existing projects).
- Prod uses Postgres via env vars: `N3_PERSIST_TARGET=postgres` and `N3_DATABASE_URL=postgres://...`.
- Edge is a placeholder target: `N3_PERSIST_TARGET=edge` and `N3_EDGE_KV_URL=...`.
- Check status: `n3 data`.
- Reset persisted data: `n3 data reset --yes` (confirmation required, SQLite only).
- Run inside the project folder (where `app.ai` is). Otherwise use `n3 <app.ai> data`.

## Grammar note
- Record fields use `is` for types and `must` for constraints, and canonical types are `text`, `number`, `boolean`, for example: `field "email" is text must be present`, `field "age" is number must be greater than 17`, `field "active" is boolean must be present`.

## Next steps
- Read [First 5 minutes](first-5-minutes.md) for a guided win.
- Run the [CRUD dashboard example](examples/demo_crud_dashboard.ai) after your first project.
- See [What you can build today](what-you-can-build-today.md) to understand supported use cases.
- Learn expressions and conditionals in [Expressions & Conditionals](expressions-and-conditionals.md).
- Learn Capsules + tests in [Modules and Tests](modules-and-tests.md).
- Learn packages in [Packages](packages.md).
- Learn identity + persistence in [Identity and Persistence](identity-and-persistence.md).
- UI details live in the [UI DSL Spec](ui-dsl.md).

## Form payloads (CLI)

- Canonical: `{"values":{"email":"ada@example.com","name":"Ada"}}`
- Also accepted (auto-wrapped): `{"email":"ada@example.com","name":"Ada"}` - prefer the canonical shape in docs/scripts.
