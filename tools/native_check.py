from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "native" / "Cargo.toml"


def main() -> int:
    if not MANIFEST.exists():
        print("native Cargo.toml not found")
        return 1
    cargo = shutil.which("cargo")
    if cargo is None:
        print("cargo not found")
        return 1
    with tempfile.TemporaryDirectory(prefix="namel3ss-native-build-") as tmp_dir:
        env = os.environ.copy()
        env["CARGO_TARGET_DIR"] = tmp_dir
        result = subprocess.run(
            [cargo, "build", "--manifest-path", str(MANIFEST)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    if result.returncode != 0:
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result.returncode
    print("native build ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
