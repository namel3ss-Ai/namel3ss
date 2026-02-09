from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ALLOWED_LANGS = {"ai", "namel3ss"}
SKIP_PREFIXES = (
    "# doc:skip",
    "# docs:skip",
    "# doc:ignore",
    "# docs:ignore",
    "# doctest: skip",
    "// doc:skip",
    "// docs:skip",
    "<!-- doc:skip -->",
)


@dataclass(frozen=True)
class DocsExample:
    path: Path
    index: int
    start_line: int
    end_line: int
    language: str
    source: str


def default_doc_paths(root: Path | None = None) -> list[Path]:
    root = root or Path(".")
    candidates: set[Path] = set()
    candidates.add(root / "docs" / "ui-dsl.md")
    candidates.add(root / "docs" / "ui-layout.md")
    candidates.add(root / "docs" / "conditional-ui.md")
    candidates.add(root / "docs" / "ui" / "conditional-ui.md")
    candidates.update(root.glob("docs/ui*.md"))
    candidates.update(root.glob("docs/ui/*.md"))
    existing = [path for path in candidates if path.exists()]
    return sorted(existing, key=lambda path: path.as_posix())


def extract_examples(path: Path, *, allowed_langs: Iterable[str] = ALLOWED_LANGS) -> list[DocsExample]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    allowed = {lang.strip().lower() for lang in allowed_langs}
    examples: list[DocsExample] = []
    in_block = False
    current_lang = ""
    buffer: list[str] = []
    start_line = 0
    end_line = 0
    index = 0

    for line_no, line in enumerate(lines, 1):
        stripped = line.strip()
        if not in_block:
            if stripped.startswith("```"):
                lang = stripped[3:].strip().split()[0] if stripped[3:].strip() else ""
                if lang.lower() in allowed:
                    in_block = True
                    current_lang = lang.lower()
                    buffer = []
                    start_line = line_no + 1
                    end_line = line_no + 1
            continue
        if stripped.startswith("```"):
            end_line = line_no - 1
            source = "\n".join(buffer).rstrip("\n")
            if source and not _is_skipped_source(source):
                index += 1
                examples.append(
                    DocsExample(
                        path=path,
                        index=index,
                        start_line=start_line,
                        end_line=max(start_line, end_line),
                        language=current_lang,
                        source=source,
                    )
                )
            in_block = False
            current_lang = ""
            buffer = []
            start_line = 0
            end_line = 0
            continue
        buffer.append(line)
    return examples


def load_examples(paths: Iterable[Path]) -> list[DocsExample]:
    collected: list[DocsExample] = []
    for path in paths:
        collected.extend(extract_examples(path))
    return collected


def _is_skipped_source(source: str) -> bool:
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        return any(stripped.startswith(prefix) for prefix in SKIP_PREFIXES)
    return False


def _main() -> int:
    paths = default_doc_paths()
    examples = load_examples(paths)
    for example in examples:
        print(
            f"{example.path}:{example.start_line}-{example.end_line} "
            f"example {example.index} ({example.language})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
