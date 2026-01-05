# namel3ss
designed to be understood

![status: alpha](https://img.shields.io/badge/status-alpha-blue)
![license: MIT](https://img.shields.io/badge/license-MIT-green)
![tests](https://github.com/namel3ss-Ai/namel3ss/actions/workflows/ci.yml/badge.svg)

---

## Why namel3ss exists

Software has changed.

AI is now part of how applications think, decide, and respond.  
But most programming languages were designed long before that.

So developers add AI with layers of glue like prompts, memory, tools, retries, and guardrails, all scattered across systems. It works.  
Until it doesn't.  
And when it fails, no one can clearly see **what happened, or why**.

**namel3ss removes the glue.**

AI, memory, UI, and logic are built into a single, deterministic model so every run can be understood, explained, and trusted.

## What is namel3ss?

namel3ss is an **AI-native programming language**.

It treats AI as a first-class concept, while keeping execution explicit, state visible, and behavior explainable.

One `.ai` file can describe:
- what the application shows
- what it does
- how AI is used
- what memory is read or written
- and why each decision happened

Nothing is hidden.

## Design guarantees

namel3ss is built around a few non-negotiable ideas:

- **Deterministic execution**  
  Every run follows a clear, stable path.

- **Explicit AI boundary**  
  AI is never implicit. Every AI call is visible and traced.

- **Explainability by default**  
  You can always ask: *what happened, and why?*

- **Governed memory**  
  Memory is explicit, inspectable, and policy-driven, not hidden context.

- **One file, one mental model**  
  UI, data, logic, tools, and AI live together, so intent stays clear.

These are not features.  
They are guarantees.

## Try it in 60 seconds

This command scaffolds ClearOrders, the reference project used by namel3ss.

```bash
pip install namel3ss
n3 new demo
cd demo
n3 run
```

On first run, the browser opens a working application with:

- an orders dataset
- an AI query flow
- deterministic execution and traceable decisions

To inspect execution, state, and reasoning, open Studio:
```bash
n3 app.ai studio
```

## About ClearOrders

ClearOrders is the reference experience for namel3ss.

It is intentionally not minimal.

It exists to demonstrate:

- AI operating over structured records
- explicit AI boundaries and deterministic execution
- explainable "Why?" outputs
- governed, inspectable memory

Understanding ClearOrders is sufficient to understand the core model of namel3ss.

## What makes it different
- One `.ai` file defines data, UI, backend logic, and AI.
- Deterministic execution environment by default; AI is explicit and traced.
- Built-in run summary and explanations for flows, tools, and UI.
- File-first CLI and Studio for inspection and interaction.
- First-run experience that opens the demo in a browser automatically.

## Quickstart (non-demo)
```bash
n3 new starter my_app
cd my_app
n3 app.ai
```

Minimal UI example:
```ai
page "home":
  title is "Hello"
  text is "Welcome"
```

Optional AI example:
```ai
ai "assistant":
  provider is "mock"
  model is "mock-model"
  system_prompt is "You are a concise assistant."

flow "reply":
  ask ai "assistant" with input: input.message as reply
  return reply
```

This is the core idea:  
intent first, execution second, explanation always.

## Who namel3ss is for
namel3ss is for:
- builders exploring AI-native application development
- developers who care about explainability and trust
- language and tooling enthusiasts
- learning, experimentation, and internal tools

namel3ss is not trying to replace Python or JavaScript.  
It is exploring what comes next.

## Status
namel3ss is in v0.1.0a7 alpha. It is suitable for learning and experimentation, not production.  
Expect breaking changes between alpha revisions.

## Start here (learning path)
- [Quickstart](docs/quickstart.md)
- [First 5 minutes](docs/first-5-minutes.md)
- [What you can build today](docs/what-you-can-build-today.md)

## Documentation index
### Getting started
- [Learning book](docs/learning-namel3ss.md)
- [Quickstart](docs/quickstart.md)
- [First 5 minutes](docs/first-5-minutes.md)
- [What you can build today](docs/what-you-can-build-today.md)
- [Examples](examples/)
- [Demo: CRUD dashboard](docs/examples/demo_crud_dashboard.md)
- [Demo: onboarding flow](docs/examples/demo_onboarding_flow.md)
- [Demo: AI assistant over records](docs/examples/demo_ai_assistant_over_records.md)
- [Documentation directory](docs/)

### UI
- [UI DSL spec](docs/ui-dsl.md)

### Explainability
- [Execution how](docs/execution-how.md)
- [Run outcome](docs/flow-what.md)
- [Tools with](docs/tools-with.md)
- [UI see](docs/ui-see.md)
- [Errors fix](docs/errors-fix.md)
- [Build exists](docs/build-exists.md)
- [CLI: exists](docs/cli-exists.md)
- [CLI: fix](docs/cli-fix.md)
- [CLI: what](docs/cli-what.md)
- [CLI: when](docs/cli-when.md)
- [CLI: with](docs/cli-with.md)

### Tools & packs
- [Python tools](docs/python-tools.md)
- [Tool packs](docs/tool-packs.md)
- [Capabilities](docs/capabilities.md)
- [Publishing packs](docs/publishing-packs.md)
- [Registry](docs/registry.md)
- [Editor](docs/editor.md)

### Deployment & promotion
- [Targets and promotion](docs/targets-and-promotion.md)

### Trust, memory & governance
**Memory in one minute:** namel3ss memory is **explicit**, **governed**, and **inspectable**. It records what matters (preferences, decisions, facts, corrections) under clear policies, with deterministic recall and traceable writes, so AI behavior can be reviewed instead of guessed. You can inspect what was recalled or written through Studio and CLI explanations.
- [Trust and governance](docs/trust-and-governance.md)
- [Memory overview](docs/memory.md)
- [Concurrency model](docs/concurrency.md)
- [AI language definition](docs/ai-language-definition.md)

### Stability & limitations
- [Stability](docs/stability.md)
- [Spec freeze v1](docs/spec-freeze-v1.md)
- [Canonical version map](resources/spec_versions.json)
- [Beta checklist](docs/beta-checklist.md)
- [Known limitations](resources/limitations.md)
- [Changelog](CHANGELOG.md)

## Community & support
- [Issues](https://github.com/namel3ss-Ai/namel3ss/issues)
- [Discussions](https://github.com/namel3ss-Ai/namel3ss/discussions/)
- [Discord](https://discord.gg/x8s6aEwdU)
- [LinkedIn](https://www.linkedin.com/company/namel3ss/)
- [Email](mailto:info@namel3ss.com)
- [Source repository](https://github.com/namel3ss-Ai/namel3ss)

## About the name
The "3" in namel3ss is intentional.

It reflects a belief:  
the basics of a programming language should be understandable in minutes, not hours.

For us, "3" is a reminder.  
If the core ideas of namel3ss cannot be understood in about three minutes, the language, not the developer, has failed.

When that happens, we redesign it.

## Contributing
Read [CONTRIBUTING.md](CONTRIBUTING.md) and [ECOSYSTEM.md](ECOSYSTEM.md).
