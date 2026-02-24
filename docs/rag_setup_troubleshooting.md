# RAG app setup troubleshooting

This guide captures the most common setup failures seen while building `rag-application` and the deterministic recovery steps.

## 1) `ModuleNotFoundError: No module named 'namel3ss'`

What it means:
- The `n3` executable on PATH does not belong to the Python environment where `namel3ss` is installed.

Fix:
```bash
source .venv/bin/activate
which -a n3
python -c "import namel3ss; print(namel3ss.__file__)"
```

Expected:
- `n3` should resolve to your active `.venv/bin/n3` first.
- `namel3ss.__file__` should resolve to the environment/repo you intend to use.

If not, reinstall into the active environment:
```bash
pip uninstall -y namel3ss
pip install -e /absolute/path/to/namel3ss
```

## 2) `use preset "rag_chat"` fails to parse

What it means:
- You are running an older build that does not include current preset grammar/expansion.

Fix:
```bash
source .venv/bin/activate
pip uninstall -y namel3ss
pip install -e /absolute/path/to/latest/namel3ss
python - <<'PY'
from namel3ss.parser.presets import rag_chat
print('ok:', rag_chat.__name__)
PY
```

Then validate app:
```bash
n3 check app.ai
```

## 3) Python version conflicts during install

Current requirement:
- `namel3ss` requires Python `>=3.14`.

Fix:
```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Verify:
```bash
python -V
n3 --version
```

## 4) Multiple local clones cause stale installs

What it means:
- You installed from a different local clone than the one you are editing.

Fix:
```bash
python -c "import namel3ss, inspect; print(inspect.getfile(namel3ss))"
```

If path is wrong, reinstall from the intended clone:
```bash
pip install -e /absolute/path/to/that/clone
```

## 5) Port already in use (`7360` etc.)

What it means:
- A previous `n3 run` process still owns the port.

Fix (macOS/Linux):
```bash
lsof -i :7360
kill <pid>
```

Or run on a different port:
```bash
n3 run app.ai --port 7361 --no-open
```

## Preventive checklist (for every new repo)

1. Create repo-local `.venv`.
2. Activate `.venv` before any `pip` or `n3` command.
3. Install `namel3ss` from source (`pip install -e /path/to/namel3ss`).
4. Run `n3 doctor` and ensure `cli_entrypoint` is `ok`.
5. Run `n3 check app.ai` before first `n3 run`.

## Canonical command order

Use:
```bash
n3 check app.ai
n3 run app.ai --port 7360 --no-open
```

This is the canonical form used in docs and CI.

## 6) "No grounded support found..." after uploading to active project

What it means:
- Upload selection is metadata-only until ingestion runs.
- In `rag_chat`, uploading to `project_files` does not become retrievable until indexing is triggered.

Fix:
1. Click **Index project files** in the sidebar (calls `rag.ingest`).
2. Ask the question again.

Alternative:
- Attach the file directly in the chat composer (`chat_files`) and send your question; this path performs ingestion during `rag.answer`.
