from __future__ import annotations

from pathlib import Path
import ast


TESTS_ROOT = Path(__file__).resolve().parent


def _iter_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        files.append(path)
    return files


def _find_examples_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name == "examples" or name.startswith("examples."):
                    offenders.append(name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "examples" or module.startswith("examples."):
                offenders.append(module or "<relative>")
    return offenders


def test_tests_do_not_import_examples() -> None:
    offenders: list[str] = []
    for path in _iter_python_files(TESTS_ROOT):
        for name in _find_examples_imports(path):
            offenders.append(f"{path}: {name}")
    assert not offenders, "Tests must not import from examples.*:\n" + "\n".join(offenders)
