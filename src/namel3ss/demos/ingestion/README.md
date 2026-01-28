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

4) Create a short file and upload it (this should block at the quality gate):
```
printf "too short\n" > sample.txt
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

7) Review the ingestion report (expected to be denied by policy), and capture the JSON payload:
```
n3 app.ai <review_action_id> '{"upload_id":"<checksum>"}' --json > audit-input.json
```
Expected denial (example):
```
Ingestion review is not permitted. Policy requires permission ingestion.review.
```

8) Attempt an override mode (expected to be denied by policy):
```
n3 app.ai <action_id> '{"upload_id":"<checksum>","mode":"ocr"}'
```

9) Explain the full decision chain (upload → ingestion → policy → retrieval):
```
n3 explain --audit --input audit-input.json --query "short"
```
