# Learning namel3ss
Build AI-native applications you can explain

This book is a single, progressive path through namel3ss. It teaches the language, runtime model, and toolchain without requiring you to read the full /docs tree. All examples use the `.ai` syntax and CLI behavior.

If something fails to run, start with `n3 doctor`.

## Part I - The Mental Model

### What namel3ss is
namel3ss is an English-first, AI-native programming language. A single `.ai` file defines your data (records), UI (pages), logic (flows), tools, and AI profiles. The deterministic core runs the same way every time; AI is the only nondeterministic boundary, and it is explicit.

### What a .ai file represents
A `.ai` file is a declarative program plus a deterministic execution model. Top-level blocks declare what the app is, not how a framework should build it.

Common top-level blocks:
- `spec is "1.0"` (declares the language contract)
- `capabilities` (enable built-in backend capabilities)
- `record "Name"` (data schema)
- `flow "name"` (logic)
- `job "name"` (background work)
- `page "name"` (UI)
- `tool "name"` and `ai "name"` (capabilities and AI boundary)
- `agent "name"` (multi-agent profiles)
- `identity "user"` (access control)
- `use module "path" as alias` (reuse)

### Browser and Studio
- `n3 run` executes flows and renders UI for the browser or service target.
- `n3 app.ai studio` opens the Studio UI to run actions, inspect state, and read traces.

Studio is a viewer and interactor. It shows the UI manifest, available actions, current state, and traces produced by runs.

### UI system
UI is semantic and deterministic. You describe intent; the runtime renders it.

Key ideas:
- Pages are structured documents with titles, intro text, and grouped sections.
- Records power tables, lists, forms, charts, and views.
- Flows power actions; the UI never runs logic on its own.
- Presets and density control spacing and rhythm at the app level.

Warnings surface in `manifest.warnings` via `/api/ui` and in action payloads via `/api/actions`.

Start here:
- [UI System](ui-system.md)
- [UI Quality](ui-quality.md)
- [Layout](ui-layout.md)
- [Copy](ui-copy.md)
- [Icons and Tones](ui-icons-and-tones.md)
- [Consistency](ui-consistency.md)
- [Templates](templates.md)
- [UI DSL](ui-dsl.md)
- [UI See](ui-see.md)

### Language Contracts
- [Application runtime](language/application-runtime.md): every valid `.ai` program is an application; the browser renders it, Studio inspects it.
- [Application Data Model](language/application-data-model.md): structured records, persistence, and deterministic ordering.
- [Application UI Model](language/application-ui-model.md): declarative pages, layout, components, and navigation with deterministic manifests.
- [Backend Capabilities](language/backend-capabilities.md): built-in HTTP, scheduling, uploads, secrets/auth helpers, jobs, and file I/O with explicit capability gates.
- [No dependencies](language/no-dependencies.md): install `namel3ss` and run apps without managing pip/npm for each project; packs extend capabilities.
- [Capability packs](language/capability-packs.md): explicit pack declarations, permissions, and inspection for local and installed packs.
- [Authentication](authentication.md): identity model, sessions, tokens, and redaction rules.
- [Data](data.md): backends, migrations, promotion safety, and snapshots.
- [Browser Protocol](runtime/browser-protocol.md): `/api/ui`, `/api/state`, `/api/action`, `/api/session`, `/api/login`, `/api/logout`, `/api/data/status`, `/api/migrations/status`, `/api/migrations/plan`, `/api/logs`, `/api/traces`, `/api/metrics`, and `/api/health` are stable and deterministic.
Windows paths: `language\application-runtime.md`, `language\application-data-model.md`, `language\backend-capabilities.md`, `language\no-dependencies.md`, `language\capability-packs.md`.

### Explainable execution
Every run emits deterministic artifacts that answer specific questions:
- How did the flow run?
- What happened and what did not happen?
- Which tools ran, and why were they allowed or blocked?
- What does the UI show, and why?
- What went wrong, and how can I recover?

Explainability is based on recorded facts, never on AI chain-of-thought.
Use `n3 status` for the last run summary, `n3 explain` for failures, and
`n3 clean` to remove runtime artifacts.
Studio also surfaces Logs, Tracing, and Metrics for each run; see Observability.

### What namel3ss deliberately does not do
- No CSS or styling DSL (UI is semantic only).
- No implicit AI behavior; AI must be declared and called explicitly.
- No unbounded loops or hidden recursion.
- No implicit type coercion.
- No wall-clock scheduling or cron; use the logical clock.
- No streaming or JSON-mode responses; `ollama` is text-only.

#### References
- [AI language definition](ai-language-definition.md)
- [Runtime model](runtime.md)
- [Application Data Model](language/application-data-model.md)
- [Application UI Model](language/application-ui-model.md)
- [Backend Capabilities](language/backend-capabilities.md)
- [UI DSL](ui-dsl.md)
- [Studio](studio.md)
- [Observability](observability.md)
- [Data](data.md)
- [Stability](stability.md)
- [Providers](providers.md)
- [Reserved words and safe naming](language/reserved-words.md)

## Part II - Your First App

### 1) Scaffold a project
```bash
n3 doctor
n3 new operations_dashboard my_app
cd my_app
```

If you want a checklist-focused path, start with onboarding:
```bash
n3 new onboarding onboarding_app
cd onboarding_app
```

### 2) Run it
```bash
n3 run
```

### 3) Open Studio
```bash
n3 app.ai studio
```

### 4) Read the app
The generated `app.ai` is small and readable. You should see a record, flows, and a page that wires forms and tables to actions.

```ai
record "Customer":
  fields:
    name is text must be present
    email is text must match pattern ".+@.+"

flow "seed_customers":
  set state.customer with:
    name is "Ada Lovelace"
    email is "ada@example.com"
  create "Customer" with state.customer as customer
  return "seeded"

page "home":
  title is "Customer Dashboard"
  card "Add customer":
    form is "Customer"
  card "Customer list":
    table is "Customer"
```

### 5) Modify one thing
Change the page title and re-run:

```ai
title is "Customer Dashboard"
```

### 6) Understand what changed
- `n3 ui` writes a UI manifest.
- `n3 see` explains what the UI shows.
- Run a flow, then `n3 how` and `n3 what` to see execution and outcome.

#### References
- [Quickstart](quickstart.md)
- [First 5 minutes](first-5-minutes.md)
- Templates: operations_dashboard, onboarding, support_inbox (`n3 new operations_dashboard`, `n3 new onboarding`, `n3 new support_inbox`)
- Demos: browser-ready apps in `src/namel3ss/demos` (copy, then `n3 check` and `n3 run`)
- Examples: single-file references in `src/namel3ss/examples` (or scaffold with `n3 new example <name>`)
- [UI DSL](ui-dsl.md)
- [Execution how](execution-how.md)
- [Run outcome](flow-what.md)

## Part III - Language Core

### File shape and declarations
A `.ai` file is a list of declarations. The engine reads these blocks and produces a deterministic program.

Minimal file:
```ai
spec is "1.0"

record "Note":
  fields:
    content is text must be present

flow "hello":
  return "ok"

page "home":
  title is "Welcome"
```

### Pages
**What it is**: Declarative UI made of semantic elements. Pages contain content and actions, but no flow logic.

**Minimal example**:
```ai
page "home":
  title is "Orders"
  text is "Review recent orders below."
  button "Refresh":
    calls flow "refresh_orders"
```

**Common mistake**: Putting `let`, `set`, or `if` inside a page. Pages are declarative only; move logic into flows.

### Records
**What it is**: Schemas for structured data. Records back forms, tables, and persistence.

**Minimal example**:
```ai
record "Customer":
  fields:
    name is text must be present
    email is text must match pattern ".+@.+"
```

**Common mistake**: Using non-canonical types like `string` or `int`. Use `text`, `number`, `boolean` (and `json` for tool schemas).

### Fields and constraints
**What it is**: Field definitions inside records with explicit validation rules.

**Minimal example**:
```ai
record "User":
  fields:
    email is text must be present
    age is number must be greater than 17
    bio is text must have length at least 10
```

**Common mistake**: Mixing constraints that do not match the type (for example, applying numeric comparisons to text).

### Flows
**What it is**: Deterministic logic that reads input, updates state, and returns values.

**Minimal example**:
```ai
flow "seed_customers":
  set state.customer with:
    name is "Ada"
    email is "ada@example.com"
  create "Customer" with state.customer as customer
  return "seeded"
```

**Common mistake**: Expecting `set customer` to persist. Persistent data is stored under `state` and written with `create`.

### Expressions
**What it is**: Deterministic values and calculations inside flows.

**Minimal example**:
```ai
flow "compute":
  let subtotal is 2 + 3 * 4
  let items is list:
    1,
    2,
  let count is list length of items
  return subtotal + count
```

**Common mistake**: Using `=` or `==` instead of English comparisons like `is`, `is greater than`, `is at least`.

### English-first flow sugar (optional)
This sugar lowers to existing statements and does not change runtime semantics.

Examples:
```ai
start a new run for goal using memory pack "agent-minimal"
plan with "planner" using goal
review in parallel with:
  "critic"
  "researcher"
keep all feedback
timeline shows:
  Start: goal
  Memory: "agent-minimal"
```

Collection access sugar:
```ai
let critic text is feedback[0].text
```

Policy intent sugar:
```ai
attempt unsafe request "https://example.com/"
expect blocked by policy
```

### Control flow

#### If / else
**What it is**: Branching based on a deterministic condition.

**Minimal example**:
```ai
if total is greater than 100:
  return "discount"
else:
  return "standard"
```

**Common mistake**: Forgetting the colon after the condition.

#### Repeat (bounded)
**What it is**: Deterministic loops with explicit bounds.

**Minimal example**:
```ai
let count is 0
repeat while count is less than 3 limit 3:
  set count is count + 1
```

**Common mistake**: Omitting the `limit` or using a non-integer limit.

#### For each
**What it is**: Iterate over a list in a stable order.

**Minimal example**:
```ai
for each item in items:
  set state.last_item is item
```

**Common mistake**: Iterating over a non-list value.

#### Match
**What it is**: Case-based branching on a value.

**Minimal example**:
```ai
match status:
  case "open":
    return "pending"
  otherwise:
    return "closed"
```

**Common mistake**: Omitting the `otherwise` case when you want a default.

#### Try / catch
**What it is**: Catch runtime errors in a flow.

**Minimal example**:
```ai
try:
  return state.value
with catch err:
  return "failed"
```

**Common mistake**: Writing `catch` without `with catch <name>:`.

#### Parallel (deterministic)
**What it is**: Run independent tasks in a stable order. Parallel blocks cannot write state and can only call pure tools.

**Minimal example**:
```ai
parallel:
  run "primary":
    let a is 1 + 1
    return a
  run "secondary":
    let b is 2 + 2
    return b
```

**Common mistake**: Writing to `state` inside a parallel task.

### Functions (compute core)
**What it is**: Pure functions for deterministic computation.

**Minimal example**:
```ai
define function "apply tax":
  input:
    subtotal is number
  output:
    total is number
  return map:
    "total" is subtotal + 1

flow "demo":
  let result is call function "apply tax":
    subtotal is 10
  return result
```

**Common mistake**: Calling tools or AI from a function (functions are pure).

### Guards and identity
**What it is**: Access control for flows and pages using identity fields, sessions, and tokens.

**Minimal example**:
```ai
identity "user":
  fields:
    subject is text must be present
    roles is json
    permissions is json
    trust_level is text must be present
  trust_level is one of "guest", "member", "admin"

flow "admin_report": requires has_role("admin")
```

**Common mistake**: Using `requires` without declaring the `identity` fields first.

### Modules
**What it is**: Reusable `.ai` files that define records, pages, tools, and functions.

**Minimal example**:
```ai
use module "modules/common.ai" as common
```

**Common mistake**: Expecting modules to define flows or AI profiles (they cannot).

#### References
- [Language core contract](language-core.md)
- [UI DSL](ui-dsl.md)
- [Expressions and conditionals](expressions-and-conditionals.md)
- [Compute core](compute-core.md)
- [Concurrency](concurrency.md)
- [Runtime model](runtime.md)
- [Identity and persistence](identity-and-persistence.md)
- [Authentication](authentication.md)
- [Modules](modules.md)
- [Modules and tests](modules-and-tests.md)
- Templates: operations_dashboard, onboarding, support_inbox (`n3 new operations_dashboard`, `n3 new onboarding`, `n3 new support_inbox`)

## Part IV - AI and Tools

### AI profiles
**What it is**: Named AI configurations with provider, model, system prompt, and memory.

**Minimal example**:
```ai
ai "assistant":
  provider is "mock"
  model is "mock-model"
  system_prompt is "You are a concise assistant."
  memory:
    short_term is 5
    semantic is true
    profile is true
```

**Notes**:
- `mock` is the deterministic provider used for tests and offline work.
- Real providers support tool calling with canonical lifecycle traces; streaming and JSON mode are not wired. `ollama` is text-only.

### Ask AI in a flow
**Minimal example**:
```ai
flow "ask_assistant":
  ask ai "assistant" with input: "Summarize this" as reply
  return reply
```

### Agents
**What it is**: Named AI agents with their own system prompts.

**Minimal example**:
```ai
agent "agent-a":
  ai is "assistant"
  system_prompt is "Capture decisions."

flow "agent_run":
  run agent "agent-a" with input: "What should we do?" as result
  return result
```

**Team of agents (deterministic order)**:
```ai
team of agents
  "planner"
  "reviewer"
  "executor"
```

**Team roles (semantic only)**:
```ai
team of agents
  agent "planner"
    role is "Plans"
  agent "reviewer"
    role is "Reviews"
```

**Rules**:
- Team is optional; when present it must list every declared agent.
- List form and explicit agent blocks cannot be mixed in the same team.
- Names are required and unique; order is deterministic.
- Roles are labels only; the runtime owns layout, accessibility, and presentation.
- Agent ids are stable slugs derived from agent names; the team id derives from the ordered agent ids.

### Tools
**What it is**: Explicit capabilities called from flows. Tools are declared in `.ai` and bound to Python functions in `.namel3ss/tools.yaml`.

**Minimal example**:
```ai
tool "greet someone":
  implemented using python
  purity is "pure"
  timeout_seconds is 10

  input:
    name is text

  output:
    message is text

flow "hello":
  let result is greet someone:
    name is "Ada"
  return result
```

Bind the tool:
```bash
n3 tools bind "greet someone" --entry "tools.sample_tool:greet"
```

### Tool permissions and capabilities
- Tools declare purity (`pure` vs `impure`).
- Capability guarantees restrict filesystem, network, subprocess, and env access.
- Apps can further downgrade capabilities in `namel3ss.toml`.
- Trust policy can enforce stricter limits in `.namel3ss/trust/policy.toml`.

### Tool packs
Built-in packs provide reusable tools (text, datetime, file). Declare the pack in `packs:` and declare the tool; no bindings are required.
Official packs live under `packs/official/` and are signed; local packs require signing or explicit trust policy.

#### References
- [AI language definition](ai-language-definition.md)
- [Supported providers](providers-supported.md)
- [Provider capabilities](providers.md)
- [Tools](tools.md)
- [Python tools](python-tools.md)
- [Python tool protocol](python-tool-protocol.md)
- [Tool packs](tool-packs.md)
- [Capabilities](capabilities.md)
- [Tools explainability](tools-with.md)
- Templates: operations_dashboard, onboarding, support_inbox (`n3 new operations_dashboard`, `n3 new onboarding`, `n3 new support_inbox`)

## Part V - Memory (Conceptual First)

### What memory is
Memory is deterministic, policy-driven, and inspectable. It records AI-relevant facts and governs how they are stored, recalled, promoted, or denied.

### Core ideas
- **Kinds**: short_term, semantic, profile.
- **Spaces**: session, user, project, system.
- **Lanes**: my, team, agent, system.
- **Governance**: proposals and approvals for team memory.
- **Packs**: reusable policy and rule bundles.
- **Persistence**: memory snapshots are recorded by the runtime and managed by namel3ss.

### Memory CLI
```bash
n3 memory "what did I just say?"
n3 memory why
n3 memory show
```

These commands write deterministic memory artifacts managed by namel3ss.
Use `n3 clean` to remove runtime artifacts.

#### References
- [Memory contract](memory.md)
- [Memory policy](memory-policy.md)
- [Memory spaces](memory-spaces.md)
- [Memory lanes](memory-lanes.md)
- [Memory phases](memory-phases.md)
- [Memory budgets](memory-budgets.md)
- [Memory packs](memory-packs.md)
- [Memory persistence](memory-persist.md)
- [Memory trust](memory-trust.md)
- [Memory agreement](memory-agreement.md)
- [Memory rules](memory-rules.md)
- [Memory handoff](memory-handoff.md)
- [Memory explanations](memory-explanations.md)
- [Memory connections](memory-connections.md)
- [Memory impact](memory-impact.md)
- [Memory proof harness](memory-proof.md)

## Part VI - Explainability

### What each command answers
- `n3 how` - How did the flow run, step by step?
- `n3 what` - What happened in the run outcome?
- `n3 with` - Which tools ran, and why were they allowed or blocked?
- `n3 see` - What does the UI show, and why?
- `n3 fix` - What went wrong, and what recovery options exist?
- `n3 exists` - Why does this build exist in its current form?
- `n3 when` - Is this program compatible with the engine spec?
- `n3 why` / `n3 explain --why` - Why is the current state allowed?

Each command is deterministic and based on recorded facts. They do not include AI chain-of-thought.

#### References
- [Execution how](execution-how.md)
- [Run outcome](flow-what.md)
- [Tools with](tools-with.md)
- [UI see](ui-see.md)
- [Errors fix](errors-fix.md)
- [CLI: what](cli-what.md)
- [CLI: with](cli-with.md)
- [CLI: exists](cli-exists.md)
- [CLI: when](cli-when.md)
- [Build exists](build-exists.md)
- [Trust and governance](trust-and-governance.md)

## Part VII - CLI Workflow

### File-first workflow
Most commands accept an optional file path, but they also auto-detect `app.ai` when run inside a project folder.

A typical loop:
```bash
n3 check
n3 run
n3 studio
n3 ui
n3 actions
n3 app.ai format
n3 app.ai lint
n3 test
```

When troubleshooting:
```bash
n3 status
n3 explain
n3 doctor
n3 fix
```

#### References
- [Quickstart](quickstart.md)
- [First 5 minutes](first-5-minutes.md)
- [Studio](studio.md)
- [Editor](editor.md)
- [CLI: fix](cli-fix.md)
- [CLI: what](cli-what.md)
- [CLI: with](cli-with.md)

## Part VIII - Packaging and Promotion (Advanced)

### Packages and capsules
Packages are reusable capsules installed under `packages/`. Use `n3 pkg` to add and install, and import with `use "name" as alias`.

### Tool packs and registry
Tool packs bundle reusable tools with explicit capabilities. Packs are installed locally, verified, and enabled. The registry is an intent index for discovery, not a package store. Use `n3 registry list | search | info` to review intent, capabilities, risk, and trust status. Install a specific pack reference with `n3 pack add name@ref`. Studio includes a Registry panel for the same data.

### Targets and promotion
Targets describe how an app runs:
- `local` for development
- `service` for long-running servers (with `/health` and `/version`)
- `edge` is a stub target

Build and promote with `n3 pack` and `n3 ship`.

#### References
- [Packages](packages.md)
- [Registry](registry.md)
- [Tool packs](tool-packs.md)
- [Publishing packs](publishing-packs.md)
- [Packaging and deployment](deployment.md)
- [Targets and promotion](targets-and-promotion.md)
- [Package model](models/package.md)
- [Capsule model](models/capsule.md)

## Part IX - Limits, Stability, and Trust

### Status and stability
The core surface is stable and the UI DSL is frozen. Remaining change areas are:
- Formatting and lint rules may evolve.
- Templates and examples may be refined.

### Spec freeze and determinism
Core contracts are frozen. The parser, IR, and trace schemas are locked by tests. Deterministic runs must remain stable for identical inputs.

### Trust and governance
- Use `n3 verify --prod` before shipping.
- Proofs and explain output are deterministic and redacted.
- Capabilities and trust policies restrict what tools can do.

### Known limits right now
- No CSS or styling DSL.
- No unbounded loops or hidden recursion.
- No implicit type coercion.
- Streaming and JSON mode are not wired; `ollama` remains text-only.
- Edge target remains a stub.

#### References
- [Stability](stability.md)
- [Spec freeze](spec-freeze.md)
- [Trust and governance](trust-and-governance.md)
- [Capabilities](capabilities.md)
- [AI language definition](ai-language-definition.md)
- [Providers](providers.md)
- [UI DSL](ui-dsl.md)
