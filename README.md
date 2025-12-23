# namel3ss
Build AI-native applications in plain English.

namel3ss (pronounced nameless) is an English-first, AI-native programming language, built from the ground up to support AI. Everything your app needs — **data, UI, backend logic, and AI** — lives together in one `.ai` file. You describe what your system is and what it should do. namel3ss makes it executable.

---

Start here:
- [Quickstart](docs/quickstart.md)
- [First 5 minutes](docs/first-5-minutes.md)
- [What you can build today](docs/what-you-can-build-today.md)
- [UI DSL Spec](docs/ui-dsl.md)
- [Examples](examples/)
- [Stability](docs/stability.md)
- [Known limitations](resources/limitations.md)
- [Targets & promotion](docs/targets-and-promotion.md)
- [Trust & governance](docs/trust-and-governance.md)

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

### Studio
A visual environment for inspecting and interacting with namel3ss programs. An early Studio ships with v0.1.0a1/a2 — usable for state inspection, traces, and interaction. It is intentionally minimal and evolving.
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
Format and lint:
```bash
n3 fmt            # alias: n3 format
n3 lint
```
Packages (capsules):
```bash
n3 deps <cmd>     # alias: n3 pkg <cmd>
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
- deps (alias: pkg)
