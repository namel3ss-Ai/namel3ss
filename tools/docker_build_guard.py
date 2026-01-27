"""
Guard Docker builds from pinning namel3ss to an unreleased PyPI version.

Fails if any Dockerfile pip install command references namel3ss as a package spec,
or if the Dockerfile does not install from the local source tree.
"""

from __future__ import annotations

import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PIP_INSTALL_RE = re.compile(r"(?:python\s+-m\s+)?pip(?:3)?\s+install\s+", re.IGNORECASE)
DISALLOWED_PREFIXES = (
    "namel3ss==",
    "namel3ss>=",
    "namel3ss<=",
    "namel3ss~=",
    "namel3ss!=",
    "namel3ss===",
    "namel3ss[",
)
LOCAL_PATH_TOKENS = (".", "./", "..", "../")


@dataclass(frozen=True)
class Violation:
    line: int
    token: str
    command: str


@dataclass(frozen=True)
class PipInstallInstruction:
    line: int
    command: str
    has_local: bool


def iter_instructions(path: Path) -> Iterable[tuple[int, str]]:
    buffer: list[str] = []
    start_line: int | None = None
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if start_line is None:
            start_line = line_no
        buffer.append(stripped)
        if stripped.endswith("\\"):
            buffer[-1] = buffer[-1].rstrip("\\").rstrip()
            continue
        yield start_line, " ".join(buffer)
        buffer = []
        start_line = None
    if buffer and start_line is not None:
        yield start_line, " ".join(buffer)


def iter_pip_install_args(instruction: str) -> Iterable[str]:
    for match in PIP_INSTALL_RE.finditer(instruction):
        remainder = instruction[match.end() :].strip()
        if not remainder:
            continue
        args = re.split(r"\s*(?:&&|\|\||;)\s*", remainder, maxsplit=1)[0]
        if args:
            yield args.strip()


def split_args(arg_string: str) -> list[str]:
    if not arg_string:
        return []
    try:
        return shlex.split(arg_string, posix=True)
    except ValueError:
        return arg_string.split()


def is_disallowed_token(token: str) -> bool:
    lowered = token.lower()
    if lowered == "namel3ss":
        return True
    return any(lowered.startswith(prefix) for prefix in DISALLOWED_PREFIXES)


def is_local_install_token(token: str) -> bool:
    if token in LOCAL_PATH_TOKENS:
        return True
    if token.startswith("./") or token.startswith("../"):
        return True
    return False


def scan_dockerfile(path: Path) -> tuple[list[Violation], bool, list[PipInstallInstruction]]:
    violations: list[Violation] = []
    local_install_found = False
    pip_instructions: list[PipInstallInstruction] = []
    for line_no, instruction in iter_instructions(path):
        for arg_string in iter_pip_install_args(instruction):
            tokens = split_args(arg_string)
            has_local = False
            idx = 0
            while idx < len(tokens):
                token = tokens[idx]
                if token.startswith("-"):
                    idx += 1
                    continue
                if token.lower() == "namel3ss" and idx + 1 < len(tokens) and tokens[idx + 1] == "@":
                    idx += 2
                    continue
                if is_local_install_token(token):
                    local_install_found = True
                    has_local = True
                if is_disallowed_token(token):
                    violations.append(Violation(line=line_no, token=token, command=instruction))
                idx += 1
            pip_instructions.append(PipInstallInstruction(line=line_no, command=instruction, has_local=has_local))
    return violations, local_install_found, pip_instructions


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    dockerfile = repo_root / "Dockerfile"
    if not dockerfile.exists():
        print("Dockerfile not found; docker build guard skipped.")
        return 0

    violations, local_install_found, pip_instructions = scan_dockerfile(dockerfile)
    if violations:
        print("Docker build guard failed: Dockerfile pins namel3ss in a pip install.", file=sys.stderr)
        for violation in violations:
            print(
                f"- Dockerfile:{violation.line} uses '{violation.token}' in `{violation.command}`",
                file=sys.stderr,
            )
        print(
            "Fix: install from the local source tree (pip install .) or add a non-PyPI fallback.",
            file=sys.stderr,
        )
        return 1

    if not local_install_found:
        print(
            "Docker build guard failed: Dockerfile must install namel3ss from the local source tree.",
            file=sys.stderr,
        )
        if pip_instructions:
            for instruction in pip_instructions:
                if instruction.has_local:
                    continue
                print(
                    f"- Dockerfile:{instruction.line} has no local install in `{instruction.command}`",
                    file=sys.stderr,
                )
        else:
            print("- Dockerfile:1 has no pip install commands.", file=sys.stderr)
        print("Fix: add `RUN python -m pip install --no-cache-dir .`.", file=sys.stderr)
        return 1

    print("Docker build guard ok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
