# namel3ss
Build AI-native applications in plain English — with explanations you can trust.

## Try it in 60 seconds

## The 10-minute demo (ClearOrders)
```bash
pip install namel3ss
n3 new demo
cd demo
n3 run
```

The first-run experience opens your browser to the ClearOrders app with orders, Ask AI, and Why? explanations ready to try.

- Orders dataset
- Ask AI + Answer
- Why? explanation

Open Studio:
```bash
n3 app.ai studio
```

## Why namel3ss
One `.ai` file describes your data, UI, backend logic, and AI behavior.
Runs are deterministic in a clear execution environment, with AI as an explicit boundary.
Explainability is built in so you can trust what happened and why.
The first-run experience is designed to feel finished, not experimental.

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
**Memory in one minute:** namel3ss memory is **explicit**, **governed**, and **inspectable**. It records what matters (preferences, decisions, facts, corrections) under clear policies, with deterministic recall and traceable writes — so AI behavior can be reviewed instead of guessed. You can inspect what was recalled or written through Studio and CLI explanations.
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

## Contributing
Read [CONTRIBUTING.md](CONTRIBUTING.md) and [ECOSYSTEM.md](ECOSYSTEM.md).
