# Ingestion Demo

This demo shows deterministic ingestion with a quality gate.

## Steps
1) Run the app:
```
n3 run app.ai
```

2) This demo declares ingestion policy directly in `app.ai` (legacy `ingestion.policy.toml` is still supported).

3) Inspect the declared policy:
```
n3 explain app.ai --json | jq '.policy'
```

4) Create a file with repeated lines and upload it (this should warn):
```
printf "repeat line with enough words\nrepeat line with enough words\nrepeat line with enough words\nunique line one\nunique line two\n" > sample.txt
curl -F "file=@./sample.txt" "http://127.0.0.1:7340/api/upload?name=sample.txt"
```

5) Find the action ids for ingestion, review, and retrieval:
```
n3 actions app.ai --json | jq '.actions[] | select(.type=="ingestion_run" or .type=="ingestion_review" or .type=="retrieval_run")'
```

6) Run ingestion using the upload checksum:
```
n3 app.ai <action_id> '{"upload_id":"<checksum>"}'
```

7) Review the ingestion report (expected to be denied by policy):
```
n3 app.ai <review_action_id> '{"upload_id":"<checksum>"}'
```
Expected denial (example):
```
Ingestion review is not permitted. Policy requires permission ingestion.review.
```

8) Attempt an override mode (expected to be denied by policy):
```
n3 app.ai <action_id> '{"upload_id":"<checksum>","mode":"ocr"}'
```

9) Verify retrieval excludes warned content unless policy allows it:
```
n3 app.ai <retrieval_action_id> '{"query":"repeat"}'
```
