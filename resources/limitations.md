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

### 2. No Persistent Database (Yet)

Data is stored in memory.

When the process restarts:

- state resets
- records reset

This is not a bug.
It keeps the system predictable and transparent while the language matures.

Persistence will arrive later, once usage patterns are proven.

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

### 5. Tool Calling for Cloud LLMs Is Limited

namel3ss fully supports tool calling with the mock provider.

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

- distributed runtime
- clustering
- load balancing
- orchestration layer

This keeps debugging human and predictable.

### 8. No Plugins or Marketplace (Yet)

There is no plugin system.

You cannot install:

- third-party extensions
- runtime add-ons
- marketplace packages

This is deliberate.

We will not add extensibility until the core language is unshakable.

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
