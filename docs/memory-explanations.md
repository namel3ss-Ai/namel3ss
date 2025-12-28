# Memory Explanations

Memory can explain its behavior in plain English.
Explanations are deterministic and rule based.
They are built from trace data.

## Where explanations appear
- In Studio traces, select a memory event and click Explain.
- The explanation uses the same data as the trace event.

## What explanations cover
- Why a recall happened
- Why a write was denied
- Why a memory was deleted
- Why a memory was forgotten
- Why a conflict was resolved
- What changed between phases

## Explanation event
The system emits a `memory_explanation` trace event.
It points to the original event by index.
It contains a title and a list of short lines.

## Determinism and safety
- Explanations use rule based templates
- Explanations never use AI output
- Sensitive text is redacted before explanations are built
