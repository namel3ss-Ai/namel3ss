# namel3ss

AI-native programming language for deterministic, inspectable applications.
Deterministic execution with explicit AI boundaries and governed runtime.

![license: MIT](https://img.shields.io/badge/license-MIT-green)
![tests](https://github.com/namel3ss-Ai/namel3ss/actions/workflows/ci.yml/badge.svg)

---

## Start here

- [Quickstart](docs/quickstart.md)
- [First 5 minutes](docs/first-5-minutes.md)
- [What you can build today](docs/what-you-can-build-today.md)
- [Stability](docs/stability.md)
- [Limitations](resources/limitations.md)

Try it in 60 seconds: [docs/quickstart.md](docs/quickstart.md).

## Get started

### Develop from source
Use this for development and testing.

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install --upgrade pip && python -m pip install -e ".[dev]"
python -m namel3ss --help
```

### Run with Docker (isolated runtime)
Use this for a clean, repeatable runtime.

```bash
docker build -t namel3ss:local .
docker run --rm namel3ss:local n3 --help
```

### Learn / explore (docs & templates)
Use the local Docker image to open Studio for a bundled demo.

```bash
docker run -d --name namel3ss_studio -p 7340:7340 \
  -v "$PWD:/workspace" -w /workspace \
  namel3ss:local n3 app/app.ai studio --host 0.0.0.0 --port 7340
docker logs namel3ss_studio
docker rm -f namel3ss_studio
```

See [docs/install-and-run.md](docs/install-and-run.md) for complete install and Studio instructions.

## Installation (summary)

Supported paths:
- Install from source (development)
- Docker (local) for an isolated runtime

Full guide: [docs/install-and-run.md](docs/install-and-run.md)

Docker quick check:
```bash
docker build -t namel3ss:local .
docker run --rm namel3ss:local n3 --help
```

## Browser Protocol

Browser Protocol is defined in [docs/runtime/browser-protocol.md](docs/runtime/browser-protocol.md).
<!-- docs\runtime\browser-protocol.md -->

## Docker & CI guarantees

- Docker builds install from local source, not PyPI.
- Docker builds are validated in CI.
- CLI smoke tests are enforced automatically.
- Wheel installs are smoke-tested in release automation.

References:
- [Dockerfile](Dockerfile)
- [CI workflow](.github/workflows/ci.yml)
- [Release workflow](.github/workflows/release.yml)
- [Docker build guard](tools/docker_build_guard.py)
- [Wheel install check](tools/wheel_install_check.py)

## Release & governance

Release invariants (enforced):
- VERSION is metadata.
- Docker builds do not depend on PyPI.
- Publish is gated by CI and guards.
- Canonical sequence: VERSION bump → tests → tag → PyPI publish → docker image → release notes.

References:
- [Release readiness](docs/release-ready.md)
- [Release workflow](.github/workflows/release.yml)

## What you can run today

- Templates: [docs/templates.md](docs/templates.md)
- Template contract: [templates/](templates/)
- Demos: [src/namel3ss/demos](src/namel3ss/demos)
- Studio (inspection UI): [docs/studio.md](docs/studio.md)

## How it works (high level)

Design guarantees:
- Deterministic execution
- Explicit AI boundary
- Inspectable state and traces
- Governed memory

Runtime guarantees:
- Stable CLI surface
- Deterministic manifests and outputs
- Read-only diagnostics and explain output
- Safe cleanup of runtime artifacts

See [docs/trust-and-governance.md](docs/trust-and-governance.md).

## UX as a Contract

UX behavior is deterministic and explainable through stable manifests and `n3 see` output.

Guarantees:
- Uploads (progress, preview metadata, async errors)
- Conditional UI (state-gated visibility)
- Reusable UI patterns (compile-time expansion)
- Accessibility by default (roles, labels, keyboard, contrast)

Detailed UX contracts: [docs/ui/overview.md](docs/ui/overview.md)

## Language Contracts

Language Contracts are defined here:
- [docs/language/application-runtime.md](docs/language/application-runtime.md)
- [docs/language/application-data-model.md](docs/language/application-data-model.md)
- [docs/language/backend-capabilities.md](docs/language/backend-capabilities.md)
- [docs/language/no-dependencies.md](docs/language/no-dependencies.md)
- [docs/language/capability-packs.md](docs/language/capability-packs.md)
<!--
docs\language\application-runtime.md
docs\language\application-data-model.md
docs\language\backend-capabilities.md
docs\language\no-dependencies.md
docs\language\capability-packs.md
-->

## Reserved identifiers

If you must use reserved identifiers, escape them with backticks and use `n3 reserved` to list them. The reserved words list is in [docs/language/reserved-words.md](docs/language/reserved-words.md).

## Documentation index

Getting started:
- [Install and run](docs/install-and-run.md)
- [Quickstart](docs/quickstart.md)

Language & grammar:
- [Grammar contract](docs/language/grammar_contract.md)
- [Application runtime](docs/language/application-runtime.md)
- [Application data model](docs/language/application-data-model.md)
- [Backend capabilities](docs/language/backend-capabilities.md)

Runtime & backend:
- [Data and migrations](docs/data.md)
- [Observability](docs/observability.md)
- [Browser protocol](docs/runtime/browser-protocol.md)

UI & Studio:
- [Studio](docs/studio.md)
- [UI DSL](docs/ui-dsl.md)

Governance & releases:
- [Release readiness](docs/release-ready.md)
- [Stability](docs/stability.md)

## Discussions & Design Conversations

GitHub Discussions is the canonical place for architectural and language design conversations. Use Discussions for design questions, trade-offs, and long-form proposals; use Issues for bugs and actionable feature requests.

Reference discussion: [https://github.com/namel3ss-Ai/namel3ss/discussions/2](https://github.com/namel3ss-Ai/namel3ss/discussions/2)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

Summary:
- Clone the repo.
- Create and activate a virtual environment.
- Install editable + run tests (`python -m pytest -q`).

## Troubleshooting

- CLI not found: follow [docs/install-and-run.md](docs/install-and-run.md).
- Icon registry missing: use Docker or install from source per [docs/install-and-run.md](docs/install-and-run.md).
- Virtualenv confusion: recreate the venv per [docs/install-and-run.md](docs/install-and-run.md).
