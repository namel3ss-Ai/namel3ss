# Model Training

`n3 train` provides deterministic custom model training and registry integration for text, image, and audio workloads.

## Capability gate
Training is opt-in. Add `training` to the app capabilities.

```ai
spec is "1.0"

capabilities:
  training

flow "demo":
  return "ok"
```

Without this token, the CLI exits before training starts.

## CLI quickstart

```bash
n3 train \
  --model-base gpt-3.5-turbo \
  --dataset data/support_tickets.jsonl \
  --epochs 3 \
  --learning-rate 2e-5 \
  --seed 13 \
  --output-name supportbot.faq_model_v2
```

You can also pass a config file:

```yaml
model_base: gpt-3.5-turbo
dataset: data/support_tickets.jsonl
epochs: 3
learning_rate: 2e-5
seed: 13
output_name: supportbot.faq_model_v2
mode: text
validation_split: 0.2
```

```bash
n3 train --config training.yaml
```

## Determinism
- Dataset rows are loaded in file order, normalized, then partitioned by a stable hash using `seed`.
- Artifact bytes are derived from canonical metadata and are deterministic for the same inputs.
- Evaluation metrics are computed on the deterministic validation partition.
- Registry writes are immutable and append-only.
- Default `created_at` is `1970-01-01T00:00:00Z` unless `N3_TRAIN_CREATED_AT` is explicitly set.

## Outputs
- Model artifact: `models/<output_name>/<version>/model.bin`
- Metadata: `models/<output_name>/<version>/metadata.json`
- Registry update: `models_registry.yaml`
- Evaluation report: `docs/reports/training_metrics_<name>_<version>.json`
- Explainability report: `docs/reports/training_explain_<name>_<version>.json`

## Data contracts
Training configuration fields:
- `model_base` (string)
- `dataset` (path)
- `epochs` (integer)
- `learning_rate` (float)
- `seed` (integer)
- `output_name` (string)
- `mode` (text | image | audio)
- `validation_split` (float)

Model registry entry (new metadata fields):
- `base_model` (string)
- `dataset_snapshot` (string hash)
- `training_seed` (integer)
- `created_at` (timestamp string)
- `metrics` (object)

## Dataset utilities
Convert existing state exports to training JSONL:

```bash
python scripts/convert_state_to_training_dataset.py \
  --input data/state_records.json \
  --output data/support_tickets.jsonl
```

Input JSON formats:
- A list of objects
- An object containing `records` or `rows` list

## Errors
- Missing required flags fail with actionable guidance.
- Missing or malformed datasets fail before any artifact is written.
- Unsupported `model_base` for selected `mode` fails validation.
- Existing `output_name` in registry fails to prevent overwrite.
