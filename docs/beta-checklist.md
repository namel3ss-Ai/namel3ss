# Beta checklist

- Graduation tests pass in tests/graduation
- Line limit tool passes
- Golden tests unchanged for phase 0
- Trace contract tests pass
- No bracket characters in human text lines
- Determinism tests pass across repeated runs
- Capability matrix shows AI language ready yes
- Capability matrix shows beta ready yes
- Examples used as proofs run without errors

Commands
python -m compileall src -q
python tools/line_limit_check.py
pytest -q
