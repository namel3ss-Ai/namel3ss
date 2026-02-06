from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_DANGEROUS_SUBPROCESS_FUNCS = {"run", "Popen", "call", "check_call", "check_output"}
_TEXT_SUFFIXES = {
    ".cfg",
    ".env",
    ".ini",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("github_token", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
)


@dataclass(frozen=True)
class SecurityScanIssue:
    path: str
    line: int
    issue_type: str
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
            "issue_type": self.issue_type,
            "message": self.message,
        }


@dataclass(frozen=True)
class SecurityScanReport:
    issues: tuple[SecurityScanIssue, ...]

    @property
    def status(self) -> str:
        return "pass" if not self.issues else "fail"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "issue_count": len(self.issues),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def run_security_hardening_scan(repo_root: Path) -> SecurityScanReport:
    issues = list(_scan_python_files(repo_root))
    issues.extend(_scan_text_files_for_secrets(repo_root))
    issues.sort(key=lambda item: (item.path, item.line, item.issue_type, item.message))
    return SecurityScanReport(issues=tuple(issues))


def _scan_python_files(repo_root: Path) -> list[SecurityScanIssue]:
    issues: list[SecurityScanIssue] = []
    for path in _iter_python_files(repo_root):
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = path.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as err:
            issues.append(
                SecurityScanIssue(
                    path=_relpath(path, repo_root),
                    line=int(getattr(err, "lineno", 0) or 0),
                    issue_type="python_parse_error",
                    message="Unable to parse file while running security scan.",
                )
            )
            continue
        issues.extend(_scan_ast(path, repo_root, tree))
    return issues


def _scan_ast(path: Path, repo_root: Path, tree: ast.AST) -> list[SecurityScanIssue]:
    rel = _relpath(path, repo_root)
    issues: list[SecurityScanIssue] = []
    subprocess_aliases, subprocess_names, os_aliases, os_names = _collect_import_aliases(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _is_eval_or_exec_call(node):
            call_name = _safe_name(node.func)
            issues.append(
                SecurityScanIssue(
                    path=rel,
                    line=node.lineno,
                    issue_type=f"dynamic_{call_name}",
                    message=f"Do not use {call_name} for runtime evaluation.",
                )
            )
            continue
        if _is_os_system_call(node, os_aliases, os_names):
            issues.append(
                SecurityScanIssue(
                    path=rel,
                    line=node.lineno,
                    issue_type="os_system_call",
                    message="Do not use os.system/os.popen; use subprocess with argv lists.",
                )
            )
            continue
        if _is_subprocess_call(node, subprocess_aliases, subprocess_names):
            if _has_shell_true(node):
                issues.append(
                    SecurityScanIssue(
                        path=rel,
                        line=node.lineno,
                        issue_type="subprocess_shell_true",
                        message="Do not call subprocess with shell=True.",
                    )
                )
            if _first_arg_is_string_command(node):
                issues.append(
                    SecurityScanIssue(
                        path=rel,
                        line=node.lineno,
                        issue_type="subprocess_string_command",
                        message="Do not pass string commands to subprocess; pass argv lists instead.",
                    )
                )
    return issues


def _scan_text_files_for_secrets(repo_root: Path) -> list[SecurityScanIssue]:
    issues: list[SecurityScanIssue] = []
    for path in _iter_text_files(repo_root):
        rel = _relpath(path, repo_root)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern_name, pattern in _SECRET_PATTERNS:
                if pattern.search(line):
                    issues.append(
                        SecurityScanIssue(
                            path=rel,
                            line=line_no,
                            issue_type="secret_pattern",
                            message=f"Detected potential secret pattern: {pattern_name}.",
                        )
                    )
    return issues


def _iter_python_files(repo_root: Path) -> Iterable[Path]:
    for base in (repo_root / "src", repo_root / "tools"):
        if not base.exists():
            continue
        yield from sorted(base.rglob("*.py"))


def _iter_text_files(repo_root: Path) -> Iterable[Path]:
    roots = [repo_root / "src", repo_root / "tools", repo_root / ".github" / "workflows", repo_root / "docs"]
    for base in roots:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() in _TEXT_SUFFIXES:
                yield path


def _collect_import_aliases(tree: ast.AST) -> tuple[set[str], set[str], set[str], set[str]]:
    subprocess_aliases: set[str] = set()
    subprocess_names: set[str] = set()
    os_aliases: set[str] = set()
    os_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name == "subprocess":
                    subprocess_aliases.add(item.asname or "subprocess")
                if item.name == "os":
                    os_aliases.add(item.asname or "os")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "subprocess":
                for item in node.names:
                    if item.name in _DANGEROUS_SUBPROCESS_FUNCS:
                        subprocess_names.add(item.asname or item.name)
            elif node.module == "os":
                for item in node.names:
                    if item.name in {"system", "popen"}:
                        os_names.add(item.asname or item.name)
    subprocess_aliases.add("subprocess")
    os_aliases.add("os")
    return subprocess_aliases, subprocess_names, os_aliases, os_names


def _is_eval_or_exec_call(node: ast.Call) -> bool:
    if isinstance(node.func, ast.Name):
        return node.func.id in {"eval", "exec"}
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return node.func.value.id == "builtins" and node.func.attr in {"eval", "exec"}
    return False


def _is_os_system_call(node: ast.Call, os_aliases: set[str], os_names: set[str]) -> bool:
    if isinstance(node.func, ast.Name):
        return node.func.id in os_names
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return node.func.value.id in os_aliases and node.func.attr in {"system", "popen"}
    return False


def _is_subprocess_call(node: ast.Call, subprocess_aliases: set[str], subprocess_names: set[str]) -> bool:
    if isinstance(node.func, ast.Name):
        return node.func.id in subprocess_names
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return node.func.value.id in subprocess_aliases and node.func.attr in _DANGEROUS_SUBPROCESS_FUNCS
    return False


def _has_shell_true(node: ast.Call) -> bool:
    for keyword in node.keywords:
        if keyword.arg != "shell":
            continue
        return isinstance(keyword.value, ast.Constant) and keyword.value.value is True
    return False


def _first_arg_is_string_command(node: ast.Call) -> bool:
    if not node.args:
        return False
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return True
    if isinstance(first, ast.JoinedStr):
        return True
    if isinstance(first, ast.BinOp):
        return _binop_contains_string(first)
    return False


def _binop_contains_string(node: ast.BinOp) -> bool:
    values = [node.left, node.right]
    for value in values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return True
        if isinstance(value, ast.JoinedStr):
            return True
        if isinstance(value, ast.BinOp) and _binop_contains_string(value):
            return True
    return False


def _safe_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return "call"


def _relpath(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


__all__ = [
    "SecurityScanIssue",
    "SecurityScanReport",
    "run_security_hardening_scan",
]
