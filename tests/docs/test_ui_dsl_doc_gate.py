from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


RELEVANT_PREFIXES = [
    "src/namel3ss/parser/",
    "src/namel3ss/ast/",
    "src/namel3ss/ir/",
    "src/namel3ss/ui/manifest.py",
    "src/namel3ss/lint/",
    "src/namel3ss/studio/web/",
]
SPEC_PATH = "docs/ui-dsl.md"


def _git_cmd(args: list[str]) -> list[str]:
    result = subprocess.run(["git"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip().splitlines()


def _changed_files() -> list[str]:
    try:
        base_ref = os.environ.get("GITHUB_BASE_REF")
        if base_ref:
            base = _git_cmd(["merge-base", "HEAD", f"origin/{base_ref}"])[0]
        else:
            base = _git_cmd(["merge-base", "HEAD", "origin/main"])[0]
        return _git_cmd(["diff", "--name-only", f"{base}...HEAD"])
    except Exception:
        try:
            return _git_cmd(["diff", "--name-only", "HEAD~1...HEAD"])
        except Exception:
            pytest.skip("git not available for doc gate")


def test_ui_dsl_doc_gate():
    files = _changed_files()
    spec_changed = SPEC_PATH in files
    offenders = []
    for f in files:
        for prefix in RELEVANT_PREFIXES:
            if f.startswith(prefix):
                offenders.append(f)
                break
    if offenders and not spec_changed:
        msg = [
            "UI DSL related files changed but docs/ui-dsl.md was not updated.",
            "Changed files:",
            *offenders,
        ]
        pytest.fail("\n".join(msg))


def test_ui_dsl_spec_exists_and_has_sections():
    path = Path(SPEC_PATH)
    assert path.exists(), "docs/ui-dsl.md is missing"
    text = path.read_text(encoding="utf-8")
    required_sections = [
        "What UI DSL is",
        "Core blocks and naming rules",
        "Allowed UI elements",
        "Core UI primitives",
        "Story progression",
        "Flow actions",
        "Global UI settings",
        "Anti-examples",
    ]
    for section in required_sections:
        assert section in text, f"Missing section '{section}' in UI DSL spec"
    assert "theme: `light`" in text
    assert "accent color: `blue`" in text
    assert "Themes: `light`, `dark`, `white`, `black`, `midnight`, `paper`, `terminal`, `enterprise`" in text
    assert "Accent colors: `blue`, `indigo`, `purple`, `pink`, `red`, `orange`, `yellow`, `green`, `teal`, `cyan`, `neutral`" in text
    assert "number:" in text
    assert "view of" in text
    assert "compose" in text
    assert "purpose is" in text
    assert "Story progression" in text
    assert "Tone must be one of" in text
    assert "Icon must be one of" in text
