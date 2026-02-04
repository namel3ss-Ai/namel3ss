## Summary
- What does this change do?
- Which files/areas does it touch?

## Files changed
- List each file once (deduplicated).
- Do not list runtime outputs (for example anything under `.namel3ss/`).

## Checks
- [ ] No grammar or semantic changes (or linked accepted RFC).
- [ ] Files stay ≤500 LOC and single responsibility.
- [ ] Tests added/updated where behavior changes.
- [ ] `python3 -m pytest -q` passed locally.
- [ ] Files changed list includes `tests/runtime/test_embedding_retrieval.py` when applicable.
- [ ] Quick-phase ingestion never writes embedding rows; only deep-phase ingestion may write embeddings.
- [ ] `python3 tools/line_limit_check.py` passed.
- [ ] Static validation behavior preserved (Studio/CLI parity).

## Notes
- Link related issues/RFCs:
- Manual verification (if any):
