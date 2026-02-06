# Console, feedback, canary, and marketplace

## Start the console

Run:

```bash
n3 console app.ai
```

Open `http://127.0.0.1:7333/console`.

You can:

- Edit `app.ai`, `.namel3ss/models.yaml`, and `feedback.yaml`
- Validate with live lint checks
- Save changes back to files and keep runtime behavior deterministic

## Collect feedback

After an AI answer in Preview, pick a rating (`excellent`, `good`, `bad`) and optional comment.

Feedback is stored in:

- `.namel3ss/feedback.jsonl`

Each row includes:

- `flow_name`
- `input_id`
- `rating`
- `comment` (optional)
- `step_count`

List feedback:

```bash
n3 feedback list --json
```

## Schedule retraining

Define thresholds in `feedback.yaml`:

```yaml
min_positive_ratio: 0.8
min_accuracy: 0.9
min_completion_quality: 0.9
```

Generate deterministic suggestions:

```bash
n3 retrain schedule --json
```

Output is written to:

- `.namel3ss/retrain.json`

## Configure canary and shadow

Set canary routing:

```bash
n3 model canary base candidate 0.1 --shadow --json
```

Disable canary:

```bash
n3 model canary base off --json
```

Canary/shadow comparisons are recorded in:

- `.namel3ss/observability/metrics/canary_results.json`

## Use marketplace

Publish an item folder that contains `manifest.yaml`:

```bash
n3 marketplace publish ./item --json
```

Approve an item for public search:

```bash
n3 marketplace approve demo.flow 0.1.0 --json
```

Search and install:

```bash
n3 marketplace search demo --json
n3 marketplace install demo.flow --version 0.1.0 --json
```

Rate and read comments:

```bash
n3 marketplace rate demo.flow 0.1.0 5 --comment "Useful" --json
n3 marketplace comments demo.flow 0.1.0 --json
```
