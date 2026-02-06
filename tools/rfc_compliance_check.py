from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

LANGUAGE_PREFIXES = (
    "src/namel3ss/parser/",
    "src/namel3ss/lexer/",
    "src/namel3ss/lang/",
    "spec/grammar/",
)
LANGUAGE_FILES = (
    "docs/language/grammar_contract.md",
    "src/namel3ss/parser/grammar_table.py",
)
RFC_APPROVAL_LABELS = {"rfc", "rfc-approved", "design-approved"}
RFC_PATH_PREFIXES = (
    "rfcs/accepted/",
    "rfcs/final/",
)
RFC_ID_RE = re.compile(r"^RFC-\d{4}$")


def _load_event() -> dict | None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return None
    try:
        return json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _event_labels(event: dict | None) -> set[str]:
    if not event:
        return set()
    pr = event.get("pull_request")
    if not isinstance(pr, dict):
        return set()
    labels = pr.get("labels")
    if not isinstance(labels, list):
        return set()
    names: set[str] = set()
    for label in labels:
        if not isinstance(label, dict):
            continue
        name = label.get("name")
        if isinstance(name, str) and name.strip():
            names.add(name.strip().lower())
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
        base = pr.get("base", {}).get("sha") if isinstance(pr, dict) else None
        head = pr.get("head", {}).get("sha") if isinstance(pr, dict) else None
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
    from_event = _diff_from_event(event)
    if from_event:
        return sorted(set(from_event))
    return _working_tree_changes()


def _is_language_surface(path: str) -> bool:
    if path in LANGUAGE_FILES:
        return True
    return any(path.startswith(prefix) for prefix in LANGUAGE_PREFIXES)


def _is_rfc_artifact(path: str) -> bool:
    if path == "DECISIONS.md":
        return True
    return any(path.startswith(prefix) for prefix in RFC_PATH_PREFIXES)


def _env_rfc_id() -> str | None:
    value = os.environ.get("N3_RFC_ID") or os.environ.get("RFC_ID")
    if not value:
        return None
    candidate = value.strip().upper()
    if RFC_ID_RE.match(candidate):
        return candidate
    return None


def _approval_found(changed: list[str], labels: set[str], rfc_id: str | None) -> tuple[bool, str]:
    if rfc_id:
        return True, f"approved via env RFC ID {rfc_id}"
    if labels & RFC_APPROVAL_LABELS:
        label = sorted(labels & RFC_APPROVAL_LABELS)[0]
        return True, f"approved via PR label '{label}'"
    if any(_is_rfc_artifact(path) for path in changed):
        return True, "approved via RFC artifact changes"
    return False, "no approval evidence"


def main() -> int:
    event = _load_event()
    changed = _changed_files(event)
    language_changes = [path for path in changed if _is_language_surface(path)]
    if not language_changes:
        print("RFC compliance: no language-surface changes detected.")
        return 0

    labels = _event_labels(event)
    rfc_id = _env_rfc_id()
    approved, reason = _approval_found(changed, labels, rfc_id)
    if approved:
        print("RFC compliance: language-surface changes allowed.")
        print(f"Reason: {reason}.")
        for path in language_changes:
            print(f"- {path}")
        return 0

    print("RFC compliance: language-surface changes require an accepted RFC.")
    print("Provide one of the following:")
    print("- set N3_RFC_ID=RFC-####")
    print("- apply PR label 'rfc-approved' (or 'rfc')")
    print("- include RFC artifact updates under rfcs/accepted/ or DECISIONS.md")
    for path in language_changes:
        print(f"- {path}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
