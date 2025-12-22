from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Dict, Any

from namel3ss.version import get_version


MIN_PYTHON = (3, 10)
PROVIDER_ENV_VARS = [
    "NAMEL3SS_OPENAI_API_KEY",
    "NAMEL3SS_OPENAI_BASE_URL",
    "NAMEL3SS_ANTHROPIC_API_KEY",
    "NAMEL3SS_GEMINI_API_KEY",
    "NAMEL3SS_MISTRAL_API_KEY",
    "NAMEL3SS_OLLAMA_HOST",
    "NAMEL3SS_OLLAMA_TIMEOUT_SECONDS",
]
STUDIO_ASSETS = ["index.html", "app.js", "styles.css"]


def _provider_status() -> Dict[str, str]:
    status: Dict[str, str] = {}
    for name in PROVIDER_ENV_VARS:
        status[name] = "present" if os.getenv(name) else "missing"
    return status


def _studio_assets_present() -> bool:
    base = Path(__file__).resolve().parent.parent / "studio" / "web"
    for fname in STUDIO_ASSETS:
        if not (base / fname).exists():
            return False
    return True


def _project_info() -> Dict[str, Any]:
    cwd = Path.cwd()
    app_ai = cwd / "app.ai"
    n3_dir = cwd / ".namel3ss"
    writable = None
    if n3_dir.exists() and n3_dir.is_dir():
        writable = os.access(n3_dir, os.W_OK)
    return {
        "cwd": str(cwd),
        "app_ai_found": app_ai.exists(),
        "namel3ss_dir_writable": writable,
    }


def _python_info() -> Dict[str, Any]:
    version_tuple = sys.version_info
    supported = version_tuple >= MIN_PYTHON
    return {
        "version": ".".join(map(str, version_tuple[:3])),
        "supported": supported,
        "min_required": ".".join(map(str, MIN_PYTHON)),
    }


def build_report() -> Dict[str, Any]:
    return {
        "version": get_version(),
        "python": _python_info(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "cli": {
            "n3_path": shutil.which("n3") or sys.argv[0],
        },
        "project": _project_info(),
        "providers": _provider_status(),
        "studio": {"assets_present": _studio_assets_present()},
    }


def _icon(ok: bool) -> str:
    return "✅" if ok else "⚠️"


def _print_human(report: Dict[str, Any]) -> None:
    python = report["python"]
    print(f"{_icon(python['supported'])} Python {python['version']} (min {python['min_required']})")
    print(f"✅ namel3ss {report['version']}")
    platform_info = report["platform"]
    print(f"✅ Platform: {platform_info['system']} {platform_info['release']} ({platform_info['machine']})")
    print(f"✅ n3 path: {report['cli']['n3_path']}")

    project = report["project"]
    app_status = _icon(project["app_ai_found"])
    print(f"{app_status} app.ai in cwd: {project['cwd']}")
    writable = project["namel3ss_dir_writable"]
    if writable is None:
        print("⚠️ .namel3ss/ directory not found (will be created when needed)")
    else:
        print(f"{_icon(writable)} .namel3ss/ writable")

    print("Providers:")
    for name, status in report["providers"].items():
        icon = "✅" if status == "present" else "⚠️"
        print(f"  {icon} {name}: {status}")

    studio_ok = report["studio"]["assets_present"]
    print(f"{_icon(studio_ok)} Studio assets present")


def run_doctor(json_mode: bool = False) -> int:
    report = build_report()
    if json_mode:
        print(json.dumps(report, sort_keys=True))
    else:
        _print_human(report)
    return 0
