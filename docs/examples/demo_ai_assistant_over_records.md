# Demo: AI Assistant over Records

## What it shows
- Records as context (Note) with validation
- Deterministic AI via mock provider
- Seed + ask flows to drive traces
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
- Inspect state and UI manifest to see how records map to actions
- Toggle theme in Studio to preview appearance
