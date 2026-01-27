FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install the language runtime via pip (pinned to VERSION).
COPY VERSION /tmp/VERSION
RUN python -m pip install --no-cache-dir "namel3ss==$(cat /tmp/VERSION)"

# Copy only the icon registry into a temporary build context.
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
