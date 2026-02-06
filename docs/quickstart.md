# namel3ss Quickstart

Run any `.ai` app with the file-first CLI.

## Troubleshooting first

- If something doesn't run, start with `n3 doctor` (use `--json` for scripts/CI).

## Create a project

- Starter project: `n3 init <project_name>`
- Scaffold: `n3 new <template> [project_name]` (templates: `operations_dashboard`, `onboarding`, `support_inbox`)
- Example: `n3 new onboarding my_app` then `cd my_app`
- Recommended first win: `n3 new operations_dashboard ops_app` then `cd ops_app`
- The app file lives at `app.ai`; commands below assume you are in the project directory.
- Multi file apps use module files like `modules/inventory.ai`.

## Scaffolded app structure

- `app.ai` - the app source.
- `expected_ui.json` - deterministic UI snapshot for consistency checks.
- `README.md` - quick run steps and template notes.
- `.gitignore` - ignores runtime artifacts and local secrets.
- `.namel3ss/` - runtime artifacts (created after you run).

Built-in icons are referenced by name only; no icon assets are copied into the app.

## First run

```bash
n3 new operations_dashboard ops_app
cd ops_app
n3 run
```

In the browser:
- Select "Create sample incident" to seed the queue.
- Review the incident list and escalation checklist.

## Automatic routes and uploads

When you declare routes in `app.ai`, they go live automatically when you run `n3 run` or `n3 start`.
Routes are read in a stable order and saved on disk so they stay the same across restarts.

If a route sets `upload is true`, the server accepts a file upload, stores it under `.namel3ss/uploads`,
and records metadata in `.namel3ss/persist`. For CSV and JSON uploads, a simple dataset schema is saved too.

Example:

```
flow "store":
  return input.upload_id

route "upload_document":
  path is "/api/documents"
  method is "POST"
  request:
    upload is json
  response:
    upload_id is text
  upload is true
  flow is "store"
```

## API docs, SDKs, and metrics

- Docs portal: `n3 docs` (opens a local portal with endpoints and try it)
- SDKs: `n3 sdk generate --lang python|typescript|go|rust --out-dir sdk`
- Postman: `n3 sdk postman --out postman.json`
- AI metrics summary: `n3 metrics`
- Console, feedback, canary, marketplace: `docs/console-feedback-marketplace.md`
- Ecosystem, tutorials, tooling: `docs/ecosystem-developer-experience.md`
- Prompt list: `n3 prompts list`
- Prompt eval: `n3 eval prompt summary_prompt --input samples.txt`
- Conventions check: `n3 conventions check`
- Response formats: `n3 formats list`

## Core commands

- Validate: `n3 app.ai check`
- UI manifest: `n3 app.ai ui`
- Actions list: `n3 app.ai actions`
- Studio (local viewer/interactor): `n3 app.ai studio`
- Console alias (opens `/console`): `n3 app.ai console`
- Run default flow (when only one flow): `n3 app.ai`
- Run specific flow (template): `n3 app.ai flow "create_sample_incident"`
- Run an action (template): `n3 app.ai page.dashboard.button.create_sample_incident '{}'`
- Run with expression explain traces: `n3 run app.ai --explain`
- Run tests: `n3 test`
- Persist list: `n3 persist list`
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
- Add a package: `n3 pkg add github:owner/repo@<tag>`
- Install packages: `n3 pkg install`
- Scaffold a package: `n3 new pkg my_capsule`
- Scaffold a plugin: `n3 plugin new node demo_plugin`
- Adoption kit: `n3 kit --format md`
- Feedback list: `n3 feedback list --json`
- Retrain scheduler: `n3 retrain schedule --json`
- Canary config: `n3 model canary base candidate 0.1 --shadow --json`
- Marketplace search/install: `n3 marketplace search demo --json` and `n3 marketplace install demo.flow --version 0.1.0 --json`
- Tutorials: `n3 tutorial list --json` and `n3 tutorial run basics --auto --json`
- Test scaffold: `n3 scaffold test hello --json`
- Deterministic package archive: `n3 package build --out dist --json`
- Language server: `n3 lsp stdio` (or `n3 lsp check app.ai --json`)

Formatter and linter:

- Format: `n3 app.ai format`
- Format check (CI): `n3 app.ai format check`
- Lint: `n3 app.ai lint`
- Lint check (CI): `n3 app.ai lint check`

Evaluation:
- Run evals: `n3 eval`
- Deterministic reports: `n3 eval --out-dir .namel3ss/outcome`
- Fast subset: `n3 eval --fast`

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

## Templates

Bundled templates you can scaffold immediately:

- Operations Dashboard: `n3 new operations_dashboard ops_app`
- Onboarding: `n3 new onboarding onboarding_app`
- Support Inbox: `n3 new support_inbox support_app`

## Examples (read-only)

Bundled examples live inside the distribution and are not copied unless you ask.

- List templates and examples: `n3 new`
- Scaffold the `hello_flow` example: `n3 new example hello_flow`
- Other examples are copy-folder only (see `src/namel3ss/examples`).

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

**Routes and AI metadata**
Add route and AI metadata blocks to keep HTTP and model intent in one place:
```text
route "list_users":
  path is "/api/users"
  method is "GET"
  request:
    page is number
  response:
    users is list<User>
    next_page is number
  flow is "get_users"

flow "summarise":
  ai:
    model is "gpt-4"
    prompt is "Summarise the input text."
  return "ok"
```

**CRUD, AI flows, and prompts**
Use CRUD and AI flow types to avoid repetition:
```text
record "User":
  id number
  name text

crud "User"

prompt "summary_prompt":
  version is "1.0.0"
  text is "Summarise the input."

llm_call "summarise":
  model is "gpt-4"
  prompt is "summary_prompt"
  output is text
```

## Next steps
- Read [First 5 minutes](first-5-minutes.md) for a guided win.
- Try another template after your first project.
- See [What you can build today](what-you-can-build-today.md) to understand supported use cases.
- Learn expressions and conditionals in [Expressions & Conditionals](expressions-and-conditionals.md).
- Learn Capsules + tests in [Modules and Tests](modules-and-tests.md).
- Learn packages in [Packages](packages.md).
- Learn identity + persistence in [Identity and Persistence](identity-and-persistence.md).
- UI details live in the [UI DSL Spec](ui-dsl.md).
- Review breaking changes and manual upgrade steps in [UPGRADE.md](../UPGRADE.md).

## Form payloads (CLI)

- Canonical: `{"values":{"email":"ada@example.com","name":"Ada"}}`
- Also accepted (auto-wrapped): `{"email":"ada@example.com","name":"Ada"}` - prefer the canonical shape in docs/scripts.
