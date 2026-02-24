# Install and run

This guide covers the supported install paths for namel3ss.

## Prerequisite

- Python `>=3.14` is required by the current release.

Verify before install:

```bash
python3.14 -V
```

## What `pip install namel3ss` includes

`pip install` installs all required Python package dependencies declared by `namel3ss`.

It does not automatically:
- change your Python runtime version,
- install optional development extras unless requested (`.[dev]`),
- install external services, API keys, or OS-level tools,
- fix PATH precedence when an older `n3` is found first.

After install, always verify:

```bash
python -V
which -a n3
n3 doctor
```

## Install from source (development / contributors)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m namel3ss --help
deactivate
```

This install path includes the default OCR runtime for scanned PDFs; no extra OCR package setup is required.

## Docker (local) — CLI

```bash
docker build -t namel3ss:local .
docker run --rm namel3ss:local n3 --help
```

If you want to run commands against local files, mount your workspace:

```bash
docker run --rm -v "$PWD:/workspace" -w /workspace namel3ss:local n3 --help
```

## Docker (local) — Studio

```bash
docker run -d --name namel3ss_studio -p 7340:7340 \
  -v "$PWD:/workspace" -w /workspace \
  namel3ss:local n3 app/app.ai studio --host 0.0.0.0 --port 7340
```

Replace `app/app.ai` with the path to your app.

```bash
docker logs namel3ss_studio
```

Open http://127.0.0.1:7340/

```bash
docker rm -f namel3ss_studio
```

## Notes on virtual environments

- Use a fresh virtual environment per repository to avoid Python package conflicts.
- Keep the virtual environment local to the repo so `n3` resolves the expected code and resources.

## When to prefer Docker vs source install

- **Docker (local):** prefer for an isolated runtime and consistent behavior across machines.
- **Install from source:** prefer for development, debugging, and running tests.

## Common RAG environment failures

If you see missing module errors, preset parse failures, wrong local clone installs, or port collisions, use the dedicated runbook:
- [RAG app setup troubleshooting](rag_setup_troubleshooting.md)
