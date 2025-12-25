# namel3ss — Limitations (by Design)

“Focus is about saying no.”
— Steve Jobs

namel3ss is opinionated.
That means some things are not possible — on purpose.

This document explains what namel3ss does not do in v0.1.0-alpha, and why that restraint is essential to what we are building.

## The Rule of 3

The “3” in namel3ss is not decoration.

It is a promise.

If you cannot understand the basics of namel3ss in 3 minutes,
we consider that a design failure — and we will redesign it.

This rule guides every decision:

the grammar

the tooling

the Studio

and yes, the limitations

## What namel3ss Is (and Is Not)

namel3ss is:

- an English-first programming language
- AI-native, not AI-bolted-on
- deterministic by default
- designed for clarity, not cleverness

namel3ss is not:

- a general-purpose replacement for Python
- a web framework
- a cloud platform
- a “do everything” system

Those choices are intentional.

## Current Limitations (v0.1.0-alpha)

### 1. No Production Guarantees (Yet)

namel3ss v0.1.0 is an alpha.

That means:

- APIs may evolve
- some breaking changes may occur
- performance tuning is not complete

This is the phase where we optimize thinking, not scaling.

### 2. Local-Only Persistence (Opt-in)

Persistence v1 is opt-in and local:

- enable with `N3_PERSIST=1` (uses SQLite at `.namel3ss/data.db`)
- no clustering or remote storage
- traces, secrets, and provider data are not persisted

Default remains in-memory and deterministic. This keeps behavior predictable unless persistence is explicitly requested.

### 7. Navigation and Theming

namel3ss does not support complex routing or arbitrary CSS theming. Pages are single-level today; styling stays minimal and semantic.

### 8. No Native Packaging

There is no native mobile/desktop packaging; namel3ss focuses on file-first, local workflows.

### 9. Type aliases are deprecated

Canonical types are `text`, `number`, `boolean` (and `json` if present). Legacy aliases (`string`/`int`/`bool`) are accepted for compatibility but are lint errors by default. Run `n3 app.ai format` to rewrite to canonical types automatically.

### 3. No Authentication or User Management (Yet)

There is no built-in:

- login system
- roles
- permissions
- sessions across processes

Why?

Because auth is a product decision, not a language primitive.
We will add it once real applications demand it.

### 4. Limited Standard Library

The standard library is intentionally small.

There is no:

- large math module
- extensive date/time API
- filesystem DSL
- networking DSL

If you need heavy computation today, namel3ss can call out to tools written in Python.

The language stays focused on application intent, not utility sprawl.

### 5. Tool Calling Scope

Tool calling works locally and for the supported cloud providers, but:

- only single tool call per turn is wired
- JSON mode/streaming are not yet supported

For real providers (OpenAI, Anthropic, Gemini, Mistral):

- tools are declared
- schemas are passed
- but providers return text output only (for now)

This avoids provider-specific chaos while we harden a universal tool-calling model.

### 6. No UI Styling Language

There is no styling DSL.

You cannot:

- define colors
- write CSS
- tweak layout details

UI in namel3ss is semantic, not decorative.

The goal is to build working applications fast — not pixel-perfect interfaces.

### 7. No Distributed or Cloud Execution

namel3ss runs:

- locally
- in a single process
- deterministically

There is no:

- distributed engine
- clustering
- load balancing
- orchestration layer

This keeps debugging human and predictable.
Tool runners can execute remotely (service/container), but the core runtime remains local and single-process.

### 8. No Public Registry (Yet)

There is no public marketplace or global registry in v0.1.0-alpha.

What exists today:
- local registry index (`.namel3ss/registry`)
- optional team registries (HTTP, opt-in)
- pack verification with v1 signatures
- explicit install/verify/enable (no auto-updates)

What does not exist yet:
- a hosted public registry
- auto-updates or background upgrades
- popularity-based ranking (no stars, no trending)

Python is optional for most users. For advanced logic, use Python tools with explicit dependencies (`pyproject.toml` or `requirements.txt`) and a per-app `.venv` via `n3 deps install`. For common tasks, built-in tool packs are available without extra dependencies. Pack tools require no bindings; app-defined tools still require `.namel3ss/tools.yaml` bindings.

## Why These Limitations Exist

Every limitation serves a purpose:

- Clarity over completeness
- Predictability over flexibility
- Understanding over abstraction
- Design over accumulation

Most platforms fail because they add features faster than they add meaning.

We are doing the opposite.

## What You Can Expect

Despite these limits, namel3ss already lets you:

- define data models
- generate working UIs automatically
- run backend logic
- call real AI models (local and cloud)
- orchestrate multi-agent workflows
- inspect state and AI traces visually
- edit your app safely in Studio
- scaffold new apps in seconds

All in one file.
In English.
With guardrails.

## The Road Ahead

Some of today’s limitations will disappear:

- persistence
- authentication
- richer providers
- deployment options

Others may never change:

- no styling DSL
- no GraphQL
- no hidden magic

That’s how focus works.

## One Last Thing

If namel3ss ever becomes hard to understand,
we won’t document it — we’ll fix it.

That’s the promise behind the 3.
