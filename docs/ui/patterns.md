# UI patterns contract

## Purpose
UI patterns are reusable UI fragments that expand deterministically at build time.

## Core rules
- Patterns contain UI items only.
- Expansion is compile-time; no runtime pattern loading or evaluation.
- Element order is preserved as written.
- Element ids are stable and derived from page name, pattern name, and element ordinal.

## Parameters
- Parameters are a closed, explicit set per pattern.
- Values are literals only (text, number, boolean) and permitted identifiers where applicable.
- Missing required parameters are deterministic errors.
- Unknown parameters are deterministic errors.
- Parameter substitution does not alter element identity stability.

## Built-in patterns
- Empty State
- Error State
- Loading State
- Results Layout
- Status Banner

## Origin metadata and explain visibility
- Expanded elements carry origin metadata: pattern name, invocation location, and parameter values.
- Explain output lists pattern expansion and its origin deterministically.
- Redaction and bounded output rules apply to parameter values.
