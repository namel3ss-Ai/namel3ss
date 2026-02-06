from __future__ import annotations

import argparse
import ast
import os
import re
import sys
import sysconfig
import tokenize
from importlib import util
from pathlib import Path


def _load_stdlib_compileall():
    stdlib_root = Path(sysconfig.get_paths()["stdlib"])
    stdlib_path = stdlib_root / "compileall.py"
    spec = util.spec_from_file_location("_stdlib_compileall", stdlib_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load stdlib compileall.")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _iter_py_files(paths: list[str]) -> list[Path]:
    items: list[Path] = []
    if not paths:
        paths = [str(Path.cwd())]
    for entry in paths:
        path = Path(entry)
        if path.is_dir():
            items.extend(path.rglob("*.py"))
        elif path.is_file() and path.suffix == ".py":
            items.append(path)
    return sorted(items, key=lambda p: str(p))


def _compile_sources(paths: list[str], *, rx: re.Pattern[str] | None, quiet: int) -> bool:
    success = True
    for path in _iter_py_files(paths):
        path_text = str(path)
        if rx and rx.search(path_text):
            continue
        try:
            with tokenize.open(path) as handle:
                source = handle.read()
            ast.parse(source, filename=path_text, mode="exec")
        except Exception as err:
            success = False
            if quiet < 2:
                print(f"*** Error compiling {path_text!r}: {err}", file=sys.stderr)
    return success


def main(argv: list[str] | None = None) -> int:
    if not os.environ.get("PYTHONDONTWRITEBYTECODE"):
        return _load_stdlib_compileall().main(argv)

    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("-q", action="count", default=0)
    parser.add_argument("-x", dest="rx", default=None)
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)

    rx = re.compile(args.rx) if args.rx else None
    ok = _compile_sources(args.paths, rx=rx, quiet=args.q or 0)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
