FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Keep VERSION available as build metadata (do not use it to pin PyPI installs).
COPY VERSION /tmp/VERSION

# Install the runtime from the local source tree for CI-safe builds.
WORKDIR /tmp/namel3ss-src
COPY pyproject.toml README.md LICENSE MANIFEST.in CHANGELOG.md VERSION /tmp/namel3ss-src/
COPY src /tmp/namel3ss-src/src
COPY resources /tmp/namel3ss-src/resources
RUN python -m pip install --no-cache-dir . \
    && rm -rf /tmp/namel3ss-src
WORKDIR /

# Copy the icon registry into a temporary build context.
COPY resources/icons /tmp/namel3ss-icons

# Install icons deterministically into the runtime-resolved location.
RUN python - <<'PY'
from __future__ import annotations

from pathlib import Path
import shutil

from namel3ss.resources import icons_root

src = Path("/tmp/namel3ss-icons")
if not src.exists():
    raise SystemExit("Icon source directory is missing.")

dest_root = icons_root()
dest_root.mkdir(parents=True, exist_ok=True)

for path in sorted(src.rglob("*"), key=lambda p: p.as_posix()):
    if path.is_dir():
        continue
    rel = path.relative_to(src)
    target = dest_root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)

if not dest_root.exists():
    raise SystemExit("Icon destination was not created.")
PY

# Smoke test the CLI to catch missing-resource regressions.
RUN python -m namel3ss --help > /dev/null

RUN useradd --create-home --uid 10001 namel3ss \
    && mkdir -p /workspace \
    && chown -R namel3ss:namel3ss /workspace

WORKDIR /workspace
USER namel3ss

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD ["n3", "--help"]

CMD ["n3"]
