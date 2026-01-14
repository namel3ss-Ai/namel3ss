# namel3ss
Designed to be understood

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

- **Frozen grammar and semantics**  
  The language grammar is stable and phase-aware (STATIC vs RUNTIME) with identical rules enforced by CLI and Studio.

- **Explicit AI boundary**  
  AI is never implicit. Every AI call is visible and traced.

- **Explainability by default**  
  You can always ask: *what happened, and why?*

- **Governed memory**  
  Memory is explicit, inspectable, and policy-driven, not hidden context.

- **One file, one mental model**  
  UI, data, logic, tools, and AI live together, so intent stays clear.

- **Frozen UI surface**  
  The UI DSL is frozen for v0.1.x; changes are additive and documented.

These are not features.  
They are guarantees.

## Runtime guarantees

namel3ss provides the following guarantees, enforced by code, tests, and governance:

- Deterministic execution with an explicit AI boundary
- Read-only diagnostics (`n3 status`, `n3 explain`)
- Safe cleanup of runtime artifacts (`n3 clean`)
- Bounded, managed runtime artifacts (safe to delete)
- Governed memory with explicit writes and recall
- Contract-stable cli, grammar, and explain outputs

These guarantees are enforced and frozen for the v0.1.x series.

## Installation

The recommended way to install `n3` is with `pipx`, which keeps it isolated and globally available:

```bash
pipx install namel3ss
```

Or via pip:

```bash
python -m pip install -U namel3ss
```

### Verify installation

```bash
n3 --version
n3 --help
```

### Windows users
If `n3` is not found, your Python `Scripts/` folder may not be in your PATH.
You can always use the fallback command:

```bash
python -m namel3ss --help
```

## Try it in 60 seconds

```bash
python -m pip install -U namel3ss
n3 --help
n3 new demo
cd demo
n3 run
```

### What happens when you run `n3 check`
- Runs STATIC validation only: grammar, structure, schema, and manifest build.
- Does not require identity/env vars or runtime state; runtime-only rules become warnings.
- Mirrors Studio load exactly.

### What happens when you run `n3 run`
- Executes flows with RUNTIME enforcement: identity/trust, permissions, capability checks, and data existence.
- Uses the same grammar and manifest you validated with `n3 check`.

First-run defaults:
- Templates and demos include state defaults or component-provided defaults (chat, charts, cards).
- No identity or secret configuration is required to load or view the UI.

## Troubleshooting

If `n3` is not recognized:

1. Check installation:
   ```bash
   python -m pip show namel3ss
   ```

2. Check location:
   ```bash
   where n3   # Windows
   which n3   # macOS/Linux
   ```

3. Fallback command:
   ```bash
   python -m namel3ss --help
   ```

Common PATH locations:
- Windows: `C:\Users\<User>\AppData\Local\Programs\Python\PythonXY\Scripts` or `%APPDATA%\Python\PythonXY\Scripts`
- macOS/Linux: `~/.local/bin`

On first run, the browser opens a working application with:

- an orders dataset
- an AI query flow
- deterministic execution and traceable decisions

## About ClearOrders

ClearOrders is the reference experience for namel3ss.

It is intentionally not minimal.

It exists to demonstrate:

- AI operating over structured records
- explicit AI boundaries and deterministic execution
- explainable "Why?" outputs
- governed, inspectable memory

Understanding ClearOrders is sufficient to understand the core model of namel3ss.

Grammar and compatibility:
- Grammar and semantics are frozen and phase-aware; see `docs/language/grammar_contract.md`.
- Backward-compatibility policy is defined in `docs/language/backward_compatibility.md`.
- Changes that affect grammar or semantics require an RFC (`docs/language/rfc_process.md`).
- CI enforces grammar contract tests and STATIC build checks for templates/examples to prevent drift.

## What makes it different
- One `.ai` file defines data, UI, backend logic, and AI.
- Deterministic execution environment by default; AI is explicit and traced.
- Built-in run summary and explanations for flows, tools, and UI.
- File-first CLI and Studio for inspection and interaction.
- First-run experience that opens the demo in a browser automatically.

## Build agents you can explain
- Agent Builder in Studio scaffolds agents from deterministic patterns.
- Agent Timeline shows memory, tool usage, merges, and handoffs as trace-backed facts.
- Memory Packs and handoff previews keep agent memory explicit and inspectable.
- Merge policies make multi-agent outputs predictable and traceable.
- Tool-call lifecycle events are canonical across providers.

## Evaluate and ship
- `n3 eval` runs deterministic evaluation suites and emits stable JSON/TXT reports.
- Eval results are wired into release gates to prevent regressions.

## Beta lock surfaces
- Agent explain payloads, tool-call lifecycle events, merge lifecycle events, memory pack events, and CLI outputs are contract-stable and enforced by tests.

## Expressions
Flows support concise, deterministic math and list transforms:
- `let:` blocks for grouped declarations (multi-line or inline comma entries)
- `between` / `strictly between` comparisons
- `**` exponentiation (right-associative; `-2 ** 2` is `-(2 ** 2)`)
- list aggregations `sum/min/max/mean/median` with strict numeric validation
- list transforms `map/filter/reduce` with scoped binders
- `calc:` formula blocks, including `state.<path> = ...` assignments

Example:
```ai
spec is "1.0"
flow "demo":
  let numbers is list:
    1
    2
    3
    10

  calc:
    doubled = map numbers with item as n:
      n * 2
    big = filter doubled with item as x:
      x is greater than 5
    state.total = reduce big with acc as s and item as v starting 0:
      s + v
    state.avg = mean(big)
    d = 2 ** 3 ** 2
    ok = state.total is between 0 and 100

  return map:
    "total" is state.total
    "avg" is state.avg
    "d" is d
    "ok" is ok
```

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
namel3ss is in alpha (v0.1.0a9). It is suitable for learning and experimentation, not production.  
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

### Deployment & production
- [Quick deployment guide](docs/quick-deployment-guide.md) - Docker and systemd deployment
- [Production deployment guide](docs/production-deployment.md) - Comprehensive production setup
- [Production readiness roadmap](docs/production-readiness-roadmap.md) - Path to v1.0
- [Targets and promotion](docs/targets-and-promotion.md)

### Trust, memory & governance
**Memory in one minute:** namel3ss memory is **explicit**, **governed**, and **inspectable**. It records what matters (preferences, decisions, facts, corrections) under clear policies, with deterministic recall and traceable writes, so AI behavior can be reviewed instead of guessed. You can inspect what was recalled or written through Studio and CLI explanations.
- [Trust and governance](docs/trust-and-governance.md)
- [Memory overview](docs/memory.md)
- [Concurrency model](docs/concurrency.md)
- [AI language definition](docs/ai-language-definition.md)

### Stability & limitations
- [Stability](docs/stability.md)
- [Expression surface v1](docs/expression-surface.md)
- [Spec freeze](docs/spec-freeze.md)
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
