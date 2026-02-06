# Determinism and Explainability

This document defines the runtime explainability contract for seeds, traces, streaming, retrieval, training, and replay.

## Configuration

Set options in `namel3ss.toml`:

```toml
[determinism]
seed = 42
explain = true
redact_user_data = false
```

- `seed`:
  - integer: use this fixed seed for AI calls.
  - string: use as deterministic salt for seed derivation.
  - `null`: derive from call inputs and context.
- `explain`: enables explain log emission.
- `redact_user_data`: masks input/output fields in explain logs.

Environment overrides:

- `N3_DETERMINISM_SEED`
- `N3_EXPLAIN`
- `N3_REDACT_USER_DATA`

## Explain Log

When explain mode is enabled, runtime writes:

- `.namel3ss/explain/last_explain.json`
- `.namel3ss/explain/<flow>_last_explain.json`

Log entries contain:

- `event_index`
- `timestamp` (logical ISO8601 timestamp)
- `stage` (`generation`, `streaming`, `retrieval`, `performance`, `job_queue`)
- `event_type`
- `inputs`
- `outputs`
- `seed`
- `provider`
- `model`
- `parameters`
- `metadata`

Retrieval events now include:

- `candidate_chunks` with `doc_id`, `chunk_id`, `page_number`, `score`, `source_url`, and `modality`
- `scores` (keyword overlap and vector score)
- `selected` chunk list used by the final answer path

## Determinism Guarantees

- Seed generation is deterministic for identical model, input, and context.
- Streaming events are ordered and carry logical timestamps.
- Explain logs use deterministic ordering and replay hashing.
- Redaction is deterministic when enabled.
- Existing `.ai` grammar remains unchanged.

## Training Explainability

Training writes a deterministic explain report:

- `docs/reports/training_explain_<model>_<version>.json`

The report includes:

- `config_hash`
- `dataset_snapshot`
- `training_seed`
- `base_model`
- `version`
- `metrics`

## Replay

Use the `replay_hash` in `last_explain.json` to compare runs.  
Two identical runs should produce identical `replay_hash` values.

Use `n3 replay` to reconstruct and validate explain logs:

```bash
n3 replay app.ai
n3 replay --log .namel3ss/explain/last_explain.json --json
```

`n3 replay` validates hash integrity by default and reports seeds plus retrieval selections for deterministic replays.
