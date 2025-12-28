# Demo: AI Assistant over Records

## What it shows
- Records as context (Note) with validation
- Deterministic AI via mock provider
- Seed + ask flows to drive traces
- Governed memory tour (preference/decision/fact + promotion + conflict + denial + phases + diff)
- UI with cards, form, table, and assistant action

## Try it in 60 seconds
```bash
n3 examples/demo_ai_assistant_over_records.ai check
n3 examples/demo_ai_assistant_over_records.ai ui
n3 examples/demo_ai_assistant_over_records.ai studio
```

## Key concepts
- Record validation (`present`, `length`)
- Deterministic AI (mock provider, stable replies)
- Flows: seed notes, ask assistant
- UI structure: sections/cards + form/table + assistant button

## Explore in Studio
- Seed the example note, then add your own notes via the form
- Click “Ask assistant” to see traces for the AI call
- Click “Memory tour” to generate preference/decision/fact writes, promotions, a conflict resolution, a denied write, phase starts, deletions, and a phase diff
- In Traces, switch to Plain view and expand `memory_recall`, `memory_write`, `memory_border_check`, `memory_promoted`, `memory_promotion_denied`, `memory_denied`, `memory_conflict`, `memory_forget`, `memory_phase_started`, `memory_deleted`, `memory_phase_diff`
- Inspect state and UI manifest to see how records map to actions
- Toggle theme in Studio to preview appearance

## Try this
1) Click “Memory tour”.
2) Open the Traces panel → Plain view.
3) Confirm `memory_write` items include `meta.event_type`, `meta.importance_reason`, and `meta.authority`.
4) Confirm `memory_write` items include `meta.space` and `meta.owner`.
5) Confirm `memory_promoted` shows `from_space`, `to_space`, and ids.
6) Confirm `memory_promotion_denied` shows a stable reason.
7) Confirm `memory_conflict` includes winner/loser ids and rule.
8) Confirm `memory_denied` shows a redacted attempted item and reason.
9) Confirm `memory_deleted` shows `superseded` and `promoted` reasons.
10) Confirm `memory_phase_started` shows `phase_id` and `reason`.
11) Confirm `memory_phase_diff` shows added/deleted/replaced counts.
