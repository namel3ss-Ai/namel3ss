from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

HINT = "Split into folder modules; one responsibility per file."


def iter_source_files(root: Path) -> Iterable[Path]:
    src_root = root / "src"
    if not src_root.exists():
        return []
    return src_root.rglob("*.py")


def rule1_dataclasses_and_execute(text: str) -> bool:
    dataclass_count = text.count("@dataclass")
    has_lower_fn = bool(re.search(r"\bdef\s+_?lower_", text))
    has_execute_fn = bool(re.search(r"\bdef\s+_?execute_", text))
    return dataclass_count >= 5 and (has_lower_fn or has_execute_fn)


def rule2_model_and_runtime(path: Path, text: str) -> bool:
    path_str = path.as_posix()
    if "/model/" not in path_str:
        return False
    has_execute_fn = bool(re.search(r"\bdef\s+_?execute_", text))
    has_run_method = bool(re.search(r"\brun\s*\(", text))
    return has_execute_fn or has_run_method


def rule3_mega_module(text: str) -> bool:
    groups = [
        "@dataclass" in text,
        bool(re.search(r"\bdef\s+_?lower_", text)),
        bool(re.search(r"\bdef\s+_?execute_", text) or "class Executor" in text),
        "def _evaluate_expression" in text or "BinaryOp" in text or "Comparison" in text,
        bool(re.search(r"\bparse_", text) or "class Parser" in text),
    ]
    return sum(groups) >= 3


def analyze_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")

    violations = []
    if rule1_dataclasses_and_execute(text):
        violations.append("rule1: many dataclasses plus execute/lower logic")
    if rule2_model_and_runtime(path, text):
        violations.append("rule2: model folder mixed with runtime execution")
    if rule3_mega_module(text):
        violations.append("rule3: mega-module patterns (multiple responsibilities)")
    return violations


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    offenders: list[tuple[Path, list[str]]] = []
    for path in iter_source_files(repo_root):
        violations = analyze_file(path)
        if violations:
            offenders.append((path, violations))

    if offenders:
        for path, violations in offenders:
            relative_path = path.relative_to(repo_root)
            joined_rules = "; ".join(violations)
            print(f"{relative_path} - {joined_rules}. {HINT}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
