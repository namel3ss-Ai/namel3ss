from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ACK_ENV = "BREAKING_CHANGE_ACK"
ACK_LABEL = "breaking-change-ack"
BREAKING_PATH_PREFIXES = (
    "src/namel3ss/parser/",
    "src/namel3ss/lexer/",
    "src/namel3ss/runtime/contracts/",
)
BREAKING_FILES = (
    "resources/spec_versions.json",
)
DOC_PATH_PREFIXES = (
    "docs/spec/",
    "docs/governance/",
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
    if not isinstance(event, dict):
        return []
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        return []
    labels = pull_request.get("labels")
    if not isinstance(labels, list):
        return []
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
    if not isinstance(event, dict):
        return []
    if "pull_request" in event:
        pull_request = event.get("pull_request", {})
        if isinstance(pull_request, dict):
            base = pull_request.get("base", {}).get("sha") if isinstance(pull_request.get("base"), dict) else None
            head = pull_request.get("head", {}).get("sha") if isinstance(pull_request.get("head"), dict) else None
            if base and head:
                return _git_lines(["git", "diff", "--name-only", f"{base}...{head}"])
    before = event.get("before")
    after = event.get("after")
    if isinstance(before, str) and isinstance(after, str) and before and after:
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


def _is_breaking_surface(path: str) -> bool:
    if path in BREAKING_FILES:
        return True
    return any(path.startswith(prefix) for prefix in BREAKING_PATH_PREFIXES)


def _is_spec_doc(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in DOC_PATH_PREFIXES)


def _ack_enabled(event: dict | None) -> bool:
    value = str(os.environ.get(ACK_ENV, "")).strip().lower()
    if value in {"1", "true", "yes"}:
        return True
    return ACK_LABEL in _event_labels(event)


def main() -> int:
    event = _load_event()
    changed = _changed_files(event)
    breaking = [path for path in changed if _is_breaking_surface(path)]
    if not breaking:
        print("Spec diff check: no breaking-surface changes detected.")
        return 0
    docs_touched = [path for path in changed if _is_spec_doc(path)]
    if not docs_touched:
        print("Spec diff check: breaking-surface changes require docs/spec or docs/governance updates.")
        for path in breaking:
            print(f"- {path}")
        return 1
    if not _ack_enabled(event):
        print("Spec diff check: breaking-surface changes require explicit acknowledgment.")
        print(f"Set {ACK_ENV}=1 or add PR label '{ACK_LABEL}'.")
        for path in breaking:
            print(f"- {path}")
        return 1
    print("Spec diff check: breaking-surface changes acknowledged with matching spec/governance docs.")
    for path in breaking:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
