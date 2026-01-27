# Ingestion Demo

This demo shows deterministic ingestion with a quality gate.

## Steps
1) Run the app:
```
n3 run app.ai
```

2) This demo includes a policy file that requires explicit permissions for review and overrides:
```
ingestion.policy.toml
```

3) Create a file with repeated lines and upload it (this should warn):
```
printf "repeat line with enough words\nrepeat line with enough words\nrepeat line with enough words\nunique line one\nunique line two\n" > sample.txt
curl -F "file=@./sample.txt" "http://127.0.0.1:7340/api/upload?name=sample.txt"
```

4) Find the action ids for ingestion, review, and retrieval:
```
n3 actions app.ai --json | jq '.actions[] | select(.type=="ingestion_run" or .type=="ingestion_review" or .type=="retrieval_run")'
```

5) Run ingestion using the upload checksum:
```
n3 app.ai <action_id> '{"upload_id":"<checksum>"}'
```

6) Review the ingestion report (expected to be denied by policy):
```
n3 app.ai <review_action_id> '{"upload_id":"<checksum>"}'
```
Expected denial (example):
```
Ingestion review is not permitted. Policy requires permission ingestion.review.
```

7) Attempt an override mode (expected to be denied by policy):
```
n3 app.ai <action_id> '{"upload_id":"<checksum>","mode":"ocr"}'
```

8) Verify retrieval excludes warned content unless policy allows it:
```
n3 app.ai <retrieval_action_id> '{"query":"repeat"}'
```
