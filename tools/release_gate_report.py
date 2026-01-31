from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

SUMMARY_RE = re.compile(r"^=+\s*(.+?)\s*=+$")
TIME_RE = re.compile(r"\s+in\s+\d+(?:\.\d+)?s\b")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except Exception:
        return path.read_text(encoding="utf-8", errors="replace")


def _parse_failures(lines: list[str]) -> list[str]:
    failures: set[str] = set()
    for line in lines:
        if not line.startswith("FAILED "):
            continue
        node = line[len("FAILED ") :].strip()
        if " - " in node:
            node = node.split(" - ", 1)[0].strip()
        if node:
            failures.add(node)
    return sorted(failures)


def _parse_summary(lines: list[str]) -> str:
    for line in reversed(lines):
        match = SUMMARY_RE.match(line.strip())
        if not match:
            continue
        summary = match.group(1).strip()
        summary = TIME_RE.sub("", summary).strip()
        return summary
    return ""


def _read_exit_code(env_value: str, path: Path) -> int | None:
    candidates = [env_value.strip()]
    file_value = _read_text(path).strip()
    if file_value:
        candidates.append(file_value)
    for value in candidates:
        if not value:
            continue
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _git_sha() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout.strip()
    except Exception:
        return ""


def _build_payload(
    *,
    commit: str,
    workflow: str,
    job: str,
    exit_code: int | None,
    summary: str,
    failures: list[str],
) -> dict:
    return {
        "commit": commit,
        "job": job,
        "pytest": {
            "exit_code": exit_code,
            "failures": failures,
            "summary": summary,
        },
        "workflow": workflow,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(
    path: Path,
    *,
    commit: str,
    workflow: str,
    job: str,
    exit_code: int | None,
    summary: str,
    failures: list[str],
) -> None:
    exit_text = str(exit_code) if exit_code is not None else "unknown"
    summary_text = summary or "missing"
    lines = [
        "Release gate report",
        f"commit: {commit}",
        f"workflow: {workflow}",
        f"job: {job}",
        f"pytest_exit_code: {exit_text}",
        f"pytest_summary: {summary_text}",
    ]
    if failures:
        lines.append("pytest_failures:")
        lines.extend(f"- {item}" for item in failures)
    else:
        lines.append("pytest_failures: []")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic release-gate reports.")
    parser.add_argument("--log", default=".namel3ss/ci_artifacts/pytest_release_gate.log")
    parser.add_argument("--exit-code-file", default=".namel3ss/ci_artifacts/pytest_exit_code.txt")
    parser.add_argument("--json", default=".namel3ss/ci_artifacts/release_report.json")
    parser.add_argument("--txt", default=".namel3ss/ci_artifacts/release_report.txt")
    args = parser.parse_args()

    log_path = Path(args.log)
    exit_code_path = Path(args.exit_code_file)
    json_path = Path(args.json)
    txt_path = Path(args.txt)

    log_text = _read_text(log_path)
    log_lines = log_text.splitlines() if log_text else []

    summary = _parse_summary(log_lines)
    failures = _parse_failures(log_lines)
    exit_code = _read_exit_code(os.environ.get("PYTEST_RELEASE_GATE_EXIT_CODE", ""), exit_code_path)

    commit = os.environ.get("GITHUB_SHA") or _git_sha()
    workflow = os.environ.get("GITHUB_WORKFLOW", "")
    job = os.environ.get("GITHUB_JOB", "")

    payload = _build_payload(
        commit=commit,
        workflow=workflow,
        job=job,
        exit_code=exit_code,
        summary=summary,
        failures=failures,
    )
    _write_json(json_path, payload)
    _write_text(
        txt_path,
        commit=commit,
        workflow=workflow,
        job=job,
        exit_code=exit_code,
        summary=summary,
        failures=failures,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
