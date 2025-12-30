from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

OVERRIDE_LABEL = "spec-freeze-override"
GRAMMAR_PREFIXES = (
    "src/namel3ss/parser/",
    "src/namel3ss/lexer/",
)
GRAMMAR_FILES = (
    "src/namel3ss/lang/keywords.py",
)


def _load_event() -> dict | None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return None
    try:
        return json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _event_labels(event: dict | None) -> list[str]:
    if not event:
        return []
    pr = event.get("pull_request")
    if not isinstance(pr, dict):
        return []
    labels = pr.get("labels", [])
    names: list[str] = []
    for label in labels:
        if isinstance(label, dict):
            name = label.get("name")
            if isinstance(name, str):
                names.append(name)
    return names


def _git_lines(args: list[str]) -> list[str]:
    try:
        output = subprocess.check_output(args, text=True)
    except subprocess.CalledProcessError:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def _diff_from_event(event: dict | None) -> list[str]:
    if not event:
        return []
    if "pull_request" in event:
        pr = event.get("pull_request", {})
        base = pr.get("base", {}).get("sha")
        head = pr.get("head", {}).get("sha")
        if base and head:
            return _git_lines(["git", "diff", "--name-only", f"{base}...{head}"])
    before = event.get("before")
    after = event.get("after")
    if before and after:
        return _git_lines(["git", "diff", "--name-only", f"{before}...{after}"])
    return []


def _working_tree_changes() -> list[str]:
    files = _git_lines(["git", "diff", "--name-only", "HEAD"])
    files.extend(_git_lines(["git", "ls-files", "--others", "--exclude-standard"]))
    return sorted(set(files))


def _changed_files(event: dict | None) -> list[str]:
    files = _diff_from_event(event)
    if files:
        return sorted(set(files))
    return _working_tree_changes()


def _is_grammar_path(path: str) -> bool:
    if path in GRAMMAR_FILES:
        return True
    return any(path.startswith(prefix) for prefix in GRAMMAR_PREFIXES)


def _override_enabled(event: dict | None) -> bool:
    if os.environ.get("SPEC_FREEZE_OVERRIDE", "").lower() in {"1", "true", "yes"}:
        return True
    return OVERRIDE_LABEL in _event_labels(event)


def main() -> int:
    event = _load_event()
    changed = _changed_files(event)
    grammar_changes = [path for path in changed if _is_grammar_path(path)]
    if not grammar_changes:
        print("Spec freeze: no grammar surface changes detected.")
        return 0
    if _override_enabled(event):
        print("Spec freeze override detected; grammar changes allowed.")
        for path in grammar_changes:
            print(f"- {path}")
        return 0
    print("Spec freeze guard: grammar surface changes require an override label.")
    print(f"Add label '{OVERRIDE_LABEL}' to the PR or set SPEC_FREEZE_OVERRIDE=1.")
    for path in grammar_changes:
        print(f"- {path}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
