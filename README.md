# namel3ss
Build AI-native applications in plain English.

namel3ss (pronounced nameless) is an English-first, AI-native programming language, built from the ground up to support AI. Everything your app needs — **data, UI, backend logic, and AI** — lives together in one `.ai` file. You describe what your system is and what it should do. namel3ss makes it executable.

---

Start here:
- [Quickstart](docs/quickstart.md)
- [First 5 minutes](docs/first-5-minutes.md)
- [What you can build today](docs/what-you-can-build-today.md)
- [UI DSL Spec](docs/ui-dsl.md)
- [Python tools](docs/python-tools.md)
- [Tool packs](docs/tool-packs.md)
- [Capabilities](docs/capabilities.md)
- [Flow explanations](docs/flow-what.md)
- [UI explanations](docs/ui-see.md)
- [Error explanations](docs/errors-fix.md)
- [Publishing packs](docs/publishing-packs.md)
- [Registry](docs/registry.md)
- [Editor](docs/editor.md)
- [Examples](examples/)
- [Stability](docs/stability.md)
- [Known limitations](resources/limitations.md)
- [Targets & promotion](docs/targets-and-promotion.md)
- [Trust & governance](docs/trust-and-governance.md)

---

## Contracts frozen
- [Spec freeze v1](docs/spec-freeze-v1.md)
- [Canonical version map](resources/spec_versions.json)

---

## Why namel3ss
Modern application development is fragmented.

One stack for the backend.  
Another for the UI.  
A separate pile for prompts, agents, memory, tool calling, orchestration, tracing.

namel3ss removes the glue. It keeps the program **readable**, the engine **deterministic**, and AI **explicit and inspectable**.

---

## What makes it different
- **One file** can define data models, UI pages, flows, and AI behavior.
- **Deterministic by design**. AI is the only non-deterministic boundary — and it’s explicit.
- **Inspectable AI**: memory, tools, and traces are visible.
- **A real toolchain**: CLI, formatter, linter, Studio.
- **If it’s hard to understand, it’s wrong.**

---

## Language · Engine · Memory · Studio

### Language
Intent-driven syntax that reads like thought.
```ai
page "home":
  title is "Hello"
  text is "Hello World"
```
Record fields use `is` for types and `must` for constraints; canonical types are `text`, `number`, and `boolean` (e.g. `field "email" is text must be present`).

### Engine
**Engine**: the system that runs a namel3ss app and enforces its rules.
It behaves consistently across AI providers.
```ai
ai "assistant":
  provider is "openai"
  model is "gpt-4.1"
  system_prompt is "You are a helpful assistant."

flow "reply":
  ask ai "assistant" with input: input.message as reply
  return reply
```

### Memory
Explicit memory with configurable recall.
```ai
ai "assistant":
  provider is "openai"
  model is "gpt-4.1"
  memory:
    short_term is 10
    semantic is true
    profile is true
```

### Memory Contract v1
Memory is deterministic, policy driven, and inspectable.
Items follow a stable contract with canonical kinds short_term, semantic, profile.

Memory is event driven and governed.
Writes are categorized as preference, decision, fact, correction, execution, rule, or context.
Importance and conflicts are resolved by deterministic rules.

Memory is spatial and owned across session, user, project, and system.
Memory lanes separate my, team, agent, and system memory.
Agent lane is private to one agent.
Handoff copies selected items to another agent lane.
Team lane writes happen only by promotion and are summarized by memory_team_summary.
Team lane changes require agreement before they become active.
Team memory actions follow trust levels for propose and approve.
Rules are short sentences stored in team or system lane.
Rule decisions emit memory_rule_applied.
Handoff emits memory_handoff_created, memory_handoff_applied, memory_handoff_rejected, and memory_agent_briefing.

Memory is phase based with deterministic deletion of superseded or expired items.
Each AI call emits memory_recall and memory_write, plus governance and border events.
Studio shows a bracketless Plain view by default and can show explanations, links, and impact.
Memory budgets keep memory fast and small.
Soft limits trigger compaction or low value removal with clear reasons.
Recall caching is deterministic per phase and lane.
Memory is saved to disk in the project folder.
Restore loads memory on startup or stops with a clear error.
A wake up report trace shows what was restored.
Studio shows the wake up report in the Traces panel.
Studio shows a Memory budget section in the Traces panel.
Memory packs provide reusable defaults for trust, agreement, budgets, lanes, phase, and rules.
Local overrides are explicit and traced.
Studio shows a Memory packs section in the Rules panel.
Memory recall can be inspected from the CLI, which stores a proof pack under `.namel3ss/memory/last.json`.
The `n3 memory why` command renders a deterministic explanation from that proof pack.
Memory proof scenarios run under `tests/memory_proof` with golden outputs for CI checks.

Plain trace example:
```
type: memory_recall
ai_profile: assistant
session: anonymous
recalled.count: 1
recalled.1.id: session:anonymous:my:short_term:1
policy.short_term: 2
policy.lanes.read_order.1: my
current_phase.phase_id: phase-1
```

Memory trust docs at docs/memory-trust.md.
Memory rules docs at docs/memory-rules.md.
Memory handoff docs at docs/memory-handoff.md.
Memory budgets docs at docs/memory-budgets.md.
Memory persistence docs at docs/memory-persist.md.
Memory packs docs at docs/memory-packs.md.
Memory explanations docs at docs/memory-explanations.md.
Memory proof harness docs at docs/memory-proof.md.
See docs/memory.md, docs/memory-policy.md, docs/memory-lanes.md, docs/memory-agreement.md, docs/memory-spaces.md, and docs/memory-phases.md for the full schema and governance rules.

### Explainable execution (Phase 3)
Flows record deterministic execution steps and can explain how they ran.
```bash
n3 run app.ai
n3 how
```

Example output:
```
How the flow ran
- Flow "demo" ran with 6 steps.
- flow "demo" started.
- if total > 1 was true.
- took then branch because condition was true.
- returned a value.
- flow "demo" ended.

What did not happen
- skipped else branch because condition was true.
```
Execution how docs at docs/execution-how.md.

### Explainable tools (Phase 4)
Tools report what ran, why it was allowed or blocked, and what happened.
```bash
n3 run app.ai
n3 with
```

Example output:
```
Tools used in the last run
- greet someone
  - intent: called tool greet someone
  - blocked
  - runner: local
  - result: blocked
  - why: network: guarantee_blocked
```
Tools with docs at docs/tools-with.md.

### Explainable flows (Phase 5)
Flows summarize intent, outcome, and what did not happen.
```bash
n3 run app.ai
n3 with
n3 what
```

Example output:
```
What the flow did
Flow: demo

Intent
- run flow "demo" to use tool "greet someone".
- audited: no.

Outcome
- status: partial.
- tools: ok 1, blocked 0, error 0.

Why
- took then branch because condition was true.

What did not happen
- skipped else branch because condition was true.
```
Flow what docs at docs/flow-what.md.

### Explainable ui (Phase 6)
UI manifests can be explained in plain English.
```bash
n3 ui app.ai
n3 see
```

Example output:
```
What the user sees
Pages
- home (3 items)

On page "home"
- title: "Welcome"
  - because: declared in page "home"
- button: "Admin"
  - enabled: no
  - because: action "page.home.button.admin" not available because requires identity.role == "admin"

What the user does not see
- Action page.home.button.admin not available because requires identity.role == "admin".
```
UI see docs at docs/ui-see.md.

### Explainable errors (Phase 7)
Errors report what went wrong, impact, and recovery options.
```bash
n3 run app.ai
n3 fix
```

Example output:
```
What went wrong

Error
- Identity is missing "role".
- kind: permission
- where: flow "admin_only"

Impact
- Action page.home.button.admin not available because requires identity.role == "admin".

Recovery options
- Provide identity: Provide identity fields and run again.
```
Errors fix docs at docs/errors-fix.md.

### Tools
Tools are explicit, local functions with schema-validated inputs/outputs. Python code lives in `tools/*.py` (no inline Python). The `.ai` file stays intent-only; Python wiring lives in `.namel3ss/tools.yaml`.
```ai
tool "greet someone":
  implemented using python
  purity is "pure"

  input:
    name is text

  output:
    message is text

flow "hello":
  let result is greet someone:
    name is "Ada"
  return result
```
Bind the tool entry once:
```bash
n3 tools bind "greet someone" --entry "tools.sample_tool:greet"
```
Install dependencies per app:
```bash
n3 deps install
```

### Provable safety (capability enforcement)
Downgrade capabilities per tool:
```toml
[capability_overrides]
"get json from web" = { no_network = true }
```
```ai
flow "demo":
  let data is get json from web:
    url is "https://example.com/data"
  return data
```
The engine blocks the call, emits a `capability_check` trace, and `n3 explain --json`
shows the effective guarantees.

### Provable sandbox (user tools)
Enforce guarantees even for arbitrary Python:
```yaml
tools:
  "greet someone":
    kind: "python"
    entry: "tools.sample_tool:greet"
    sandbox: true
```
If the tool attempts a forbidden IO operation, the sandbox blocks it and emits a
`capability_check` trace.

### Publish a pack locally in 60 seconds
```bash
n3 packs init team.pack
n3 packs validate ./team.pack --strict
n3 packs sign ./team.pack --key-id "maintainer.alice" --private-key ./alice.key
n3 packs bundle ./team.pack --out ./dist
n3 packs add ./dist/team.pack-0.1.0.n3pack.zip
```

### Discover packs by intent
```bash
n3 registry add ./dist/team.pack-0.1.0.n3pack.zip
n3 discover "send email securely"
n3 packs add team.pack@0.1.0
```

### No wiring pain
Define tools in English, then let namel3ss wire them up:
```ai
tool "summarize a csv file":
  implemented using python

  input:
    file path is text

  output:
    rows is number
    columns is number
```
```bash
n3 tools bind --auto
n3 run app.ai
```

### Deploy tools remotely
Run tools via a service runner:
```bash
n3 tools set-runner "greet someone" --runner service --url http://127.0.0.1:8787/tools
n3 run app.ai
```

### Find and use tools
Discover available tools and search by intent:
```bash
n3 tools list
n3 tools search "date"
```

### Tool health
Catch collisions and binding issues early:
```bash
n3 lint --strict-tools
```

### No Python required
Zero Python required: use built-in tool packs for common tasks. Example:
```ai
tool "get current date and time":
  implemented using python

  input:
    timezone is optional text

  output:
    iso is text

flow "demo":
  let result is get current date and time:
    timezone is "utc"
  return result
```
Built-in packs are pre-bound — no wiring required.
10-second demo:
```bash
n3 run app.ai
```

### Marketplace (local)
Install and enable local tool packs (verified + trusted):
```bash
n3 packs add ./my_pack
n3 packs verify my.pack
n3 packs enable my.pack
```
Then declare the tool in English in `app.ai` and call it in a flow.

### Studio
A visual command center for inspecting and interacting with namel3ss programs. Studio now includes the Graph view, Trust dashboard, Data & Identity cockpit, and Guided Fixes powered by the editor service. See `docs/studio.md` for the full tour.
```bash
n3 app.ai studio
```

---

## 10-second demo
```bash
pip install namel3ss  # installs v0.1.0 alpha (a1/a2)
n3 new crud
n3 crud/app.ai studio
```
You just generated a working app and opened Studio to run it, inspect state, and see traces. If you hit installation or environment issues, please report them — that's part of alpha feedback.

## Try it in 60 seconds
```bash
pip install namel3ss  # installs v0.1.0 alpha
n3 new crud my_app
n3 my_app/app.ai studio
```

---

## The Rule of 3
The "3" in namel3ss is not decoration. It's a promise.

If you cannot understand the basics of namel3ss in 3 minutes, we consider that a design failure — and we will redesign it.

In v0.1.0 alpha (a1/a2), the Rule of 3 applies primarily to language structure, mental model, and tooling flow. Full computational expressiveness is out of scope for this alpha.

---

## What you can build today
CRUD dashboards (records → forms/tables → validation). Internal tools and admin panels. AI assistants over your records (with memory and traces). Multi-agent workflows (sequential + parallel orchestration). Prototypes that stay readable as they grow.

In v0.1.0 alpha (a1/a2), namel3ss prioritizes structural clarity and intent over computation. Arithmetic operations, conditional logic (if/else, loops), and reusable functions/modules are intentionally limited or not yet supported. This is a design choice — full computational expressiveness is planned for future versions.

---

## What’s intentionally missing
namel3ss is focused. Some things are not here yet — on purpose. Before using it for production systems, read the [known limitations](resources/limitations.md).

---

## Quickstart
- [Quickstart guide](docs/quickstart.md)
- [Examples](examples/)
- [Examples you can run](#examples-you-can-run)
- [Learning book](resources/books/learning_namel3ss_v0.1.0.md)
- More links are listed below.

---

## Examples you can run
- CRUD dashboard: [docs/examples/demo_crud_dashboard.md](docs/examples/demo_crud_dashboard.md)
- Onboarding flow: [docs/examples/demo_onboarding_flow.md](docs/examples/demo_onboarding_flow.md)
- AI assistant over records: [docs/examples/demo_ai_assistant_over_records.md](docs/examples/demo_ai_assistant_over_records.md)

---

## Core CLI (short, file-first)
Run an app (auto-detects `app.ai` in the folder):
```bash
n3 run            # or n3 run app.ai
```
Validate:
```bash
n3 check          # or n3 app.ai check
```
UI manifest and actions:
```bash
n3 ui             # or n3 app.ai ui
n3 actions        # or n3 app.ai actions
```
Run Studio:
```bash
n3 studio         # or n3 app.ai studio
```
Why mode:
```bash
n3 why            # or n3 explain --why
```
How mode:
```bash
n3 how
```
With mode:
```bash
n3 with
```
Memory recall and explain:
```bash
n3 memory "hello"
n3 memory why
n3 memory show
n3 memory @assistant "hello"
```
Format and lint:
```bash
n3 fmt            # alias: n3 format
n3 lint
```
Python deps:
```bash
n3 deps <cmd>     # status/install/sync/lock/clean
```
Packages (capsules):
```bash
n3 pkg search auth
n3 pkg info auth-basic
n3 pkg add auth-basic
```
Scaffold a package:
```bash
n3 new pkg my_capsule
```
Patterns and kits:
```bash
n3 pattern list
n3 pattern new admin-dashboard my_admin
n3 kit --format md
```
Targets and promotion:
```bash
n3 pack --target service   # alias: n3 build
n3 ship --to service       # alias: n3 promote
n3 where                   # alias: n3 status
```

---

## Providers and secrets
namel3ss supports local and cloud providers (including Ollama and Tier-1 cloud providers). Secrets should not be stored in `.ai`. Use environment variables or a local `.env` file next to `app.ai`. Templates generated by `n3 new` include `.gitignore` rules to keep `.env` out of git.

---

## Status
namel3ss is currently in v0.1.0 alpha, including v0.1.0a1 and v0.1.0a2. These are design-validation releases. Breaking changes are expected between alpha revisions. Feedback from a1/a2 directly shapes upcoming versions.

v0.1.0 alpha is intended for experimentation, learning, and language & tooling feedback. It is not production-ready. It is stable enough for early adopters, prototypes, internal tools, and learning — and it is evolving fast.

---

## Alpha testers wanted
namel3ss is in early alpha (v0.1.0a1/a2). Breaking changes will happen. Documentation may lag.

These releases are intended for experimentation, learning, and language & tooling feedback. namel3ss is not production-ready at this stage.

If you like testing early systems and giving honest, technical feedback, we want your input.

**Get involved**
- [Report a bug (GitHub Issues)](https://github.com/namel3ss-Ai/namel3ss/issues)
- [Join design discussions (GitHub Discussions)](https://github.com/namel3ss-Ai/namel3ss/discussions/)
- [Join the community on Discord](https://discord.gg/x8s6aEwdU)

## How to get help
- [Issues](https://github.com/namel3ss-Ai/namel3ss/issues)
- [Discussions](https://github.com/namel3ss-Ai/namel3ss/discussions/)
- [Discord](https://discord.gg/x8s6aEwdU)

**Try these three things**
1. Run the simplest example (or scaffold `n3 new crud`) and note anything unclear or broken.
2. Change a small flow or syntax and see how the engine responds; report surprises.
3. Call an AI profile with a basic prompt and share any errors or friction you hit.

---

## Contributing
Read the [contributing guidelines](CONTRIBUTING.md). Keep files small, focused, and disciplined. namel3ss stays readable by design.
See the ecosystem rules in [ECOSYSTEM.md](ECOSYSTEM.md) before publishing packages.

---

## Community
Join the conversation. Share ideas. Build together.

<p>
  <a href="https://discord.gg/x8s6aEwdU"><img src="https://img.shields.io/badge/Discord-Join%20us-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://www.linkedin.com/company/namel3ss/"><img src="https://img.shields.io/badge/LinkedIn-Follow-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn"></a>
</p>

---

## Links
- [Source repository](https://github.com/namel3ss-Ai/namel3ss)
- [Documentation](https://github.com/namel3ss-Ai/namel3ss/tree/main/docs)
- [Issue tracker](https://github.com/namel3ss-Ai/namel3ss/issues)
- [Changelog](https://github.com/namel3ss-Ai/namel3ss/blob/main/CHANGELOG.md)
- [Discord community](https://discord.gg/x8s6aEwdU)
- [LinkedIn page](https://www.linkedin.com/company/namel3ss/)

### Command map
- ship (alias: promote)
- pack (alias: build)
- where (alias: status)
- fmt (alias: format)
- pkg
- deps
