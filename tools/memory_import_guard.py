import ast
from dataclasses import dataclass
from pathlib import Path

ALLOWED_IMPORTS = {
    "namel3ss.runtime.memory.api",
    "namel3ss.runtime.memory.types",
}
MEMORY_PREFIX = "namel3ss.runtime.memory"


@dataclass(frozen=True)
class ImportViolation:
    path: Path
    line: int
    module: str


def find_violations(root: Path) -> list[ImportViolation]:
    violations: list[ImportViolation] = []
    for path in sorted(root.rglob("*.py")):
        if _is_memory_subsystem(path, root):
            continue
        violations.extend(_scan_file(path))
    return violations


def _scan_file(path: Path) -> list[ImportViolation]:
    violations: list[ImportViolation] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                if _is_disallowed(module):
                    violations.append(ImportViolation(path=path, line=node.lineno, module=module))
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.module:
                continue
            module = node.module or ""
            if _is_disallowed(module):
                violations.append(ImportViolation(path=path, line=node.lineno, module=module))
    return violations


def _is_disallowed(module: str) -> bool:
    if module == MEMORY_PREFIX:
        return True
    if module.startswith(f"{MEMORY_PREFIX}."):
        return module not in ALLOWED_IMPORTS
    return False


def _is_memory_subsystem(path: Path, root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    if len(rel.parts) < 3:
        return False
    if rel.parts[0] != "namel3ss" or rel.parts[1] != "runtime":
        return False
    return rel.parts[2].startswith("memory")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src"
    violations = find_violations(src_root)
    if violations:
        print("Memory import guard failed.")
        for violation in violations:
            rel = violation.path.relative_to(repo_root)
            print(f"- {rel}:{violation.line} imports {violation.module}")
        print("Fix: import only namel3ss.runtime.memory.api or namel3ss.runtime.memory.types.")
        return 1
    print("Memory import guard ok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
