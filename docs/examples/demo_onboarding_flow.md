# Demo: Multi-step Onboarding Flow

## What it shows
- Multi-section onboarding with form save + confirmation
- State carried across steps (`step`, `profile`, `confirmed`)
- Deterministic reset flow
- Pure UI + logic (no AI)

## Try it in 60 seconds
```bash
n3 examples/demo_onboarding_flow.ai check
n3 examples/demo_onboarding_flow.ai ui
n3 examples/demo_onboarding_flow.ai studio
```

## Key concepts
- Record validation (`present`, `pattern`, `length`)
- Flows: save profile, confirm, reset
- UI structure: sections + cards for steps
- Deterministic flows without external services

## Explore in Studio
- Fill the profile form and save; watch state update
- Confirm profile to mark completion; see traces
- Reset to clear session state and repeat
- Inspect actions list and UI manifest
