# No Dependencies Promise

Installing `namel3ss` is sufficient to run `.ai` applications. App authors never manage pip or npm dependencies to get an app running.

## What this promise covers
- `pipx install namel3ss` (or `python -m pip install -U namel3ss`) ships the language runtime, browser renderer, and Studio inspector together.
- OCR runtime for scanned PDFs ships with `namel3ss`; app authors do not install separate OCR tooling.
- `.ai` files declare data, flows, UI, tools, and AI without a `requirements.txt` or `package.json`.
- `n3 run` / `n3 dev` / `n3 preview` use the bundled runtime and built-in packs; no per-app downloads or hidden installs.

## Extensibility path
- New capabilities arrive as packs, not imports. Examples: `n3 pack add postgres`, `n3 pack add stripe`, `n3 pack add whatsapp`.
- Packs bundle their own bindings and capability declarations; they are permissioned and deterministic.
- Helper code lives in packs; apps stay dependency-free and English-first.

## Operational notes
- `n3 deps` reports the engine environment; it does not expect app-managed dependencies.
- Templates and demos run without secrets or third-party installs. Identity and credentials are provided explicitly when needed, not via implicit dependencies.
