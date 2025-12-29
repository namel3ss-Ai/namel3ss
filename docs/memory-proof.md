# Memory Proof Harness

The memory proof harness runs deterministic scenarios and compares outputs against goldens.
It is meant to catch behavioral changes without changing memory behavior.

## Where files live
- Scenarios: `tests/memory_proof/scenarios/*.yaml`
- Goldens: `tests/memory_proof/golden/<scenario_id>/`
- Output: `tests/memory_proof/output/<scenario_id>/`

## Commands
Generate or update goldens:
```bash
python3 tools/memory_proof_generate.py
```

Check against goldens (for CI):
```bash
python3 tools/memory_proof_check.py
```

## Scenario format
Each scenario is a small YAML file with a strict shape:
- `name`: scenario label
- `ai_profile`: name + memory settings
- `identity` and `initial_state` are optional
- `steps`: list of `recall`, `record`, or `admin` steps

Example:
```yaml
name: "Basic recall"
ai_profile:
  name: "assistant"
  memory:
    short_term: 1
    semantic: false
    profile: false
steps:
  - record:
      input: "Hello, remember this."
      output: "ok"
      tool_events: []
  - recall:
      input: "What did I just say?"
```

## Artifacts
Each scenario writes a stable bundle:
- `recall_steps.json`
- `write_steps.json`
- `meta.json`
- `plain.txt`
- `report.txt`
- `report.json`

## Invariants and semantic diff
Invariants check determinism, lane isolation, cache version monotonicity, and shape.
The diff explains what changed and how to fix it.
If a change is intended, regenerate goldens.
