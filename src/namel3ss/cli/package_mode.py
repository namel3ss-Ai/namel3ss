from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import zipfile

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.cli.text_output import prepare_cli_text


def run_package_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params["subcommand"] == "help":
            _print_usage()
            return 0
        if params["subcommand"] != "build":
            raise Namel3ssError(_unknown_subcommand_message(str(params["subcommand"])))

        project_root = Path.cwd().resolve()
        app_path = project_root / "app.ai"
        if not app_path.exists():
            raise Namel3ssError(_missing_app_message())

        out_dir = (project_root / str(params["out_dir"])) if not Path(str(params["out_dir"])).is_absolute() else Path(str(params["out_dir"]))
        out_dir.mkdir(parents=True, exist_ok=True)
        archive_name = f"{project_root.name}.n3pkg.zip"
        archive_path = out_dir / archive_name

        files = _collect_files(project_root)
        digest = _write_archive(project_root, archive_path, files)
        payload = {
            "ok": True,
            "archive": archive_path.as_posix(),
            "file_count": len(files),
            "sha256": digest,
        }
        if bool(params["json_mode"]):
            print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
            return 0
        print(f"Built {archive_path}")
        print(f"Files: {len(files)}")
        print(f"Digest: {digest}")
        return 0
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> dict[str, object]:
    if not args or args[0] in {"help", "-h", "--help"}:
        return {"subcommand": "help", "out_dir": "dist", "json_mode": False}
    subcommand = args[0].strip().lower()
    json_mode = False
    out_dir = "dist"
    i = 1
    while i < len(args):
        token = args[i]
        if token == "--json":
            json_mode = True
            i += 1
            continue
        if token == "--out":
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_option_value_message(token))
            out_dir = args[i + 1]
            i += 2
            continue
        if token.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(token))
        raise Namel3ssError(_unexpected_arg_message(token))
    return {"subcommand": subcommand, "out_dir": out_dir, "json_mode": json_mode}


def _collect_files(project_root: Path) -> list[Path]:
    files: list[Path] = []
    skip_dirs = {".git", ".namel3ss", "dist", "__pycache__", ".pytest_cache"}
    for path in sorted(project_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(project_root)
        if any(part in skip_dirs for part in rel.parts):
            continue
        files.append(path)
    return files


def _write_archive(project_root: Path, archive_path: Path, files: list[Path]) -> str:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            rel = file_path.relative_to(project_root).as_posix()
            info = zipfile.ZipInfo(rel)
            info.date_time = (2000, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, file_path.read_bytes())
    return _sha256(archive_path)


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _missing_app_message() -> str:
    return build_guidance_message(
        what="app.ai was not found.",
        why="package build runs from a project root.",
        fix="Change to your project folder first.",
        example="cd my_app && n3 package build",
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown package command '{subcommand}'.",
        why="Supported command: build.",
        fix="Run n3 package help.",
        example="n3 package build",
    )


def _missing_option_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} needs a value.",
        why="A destination path is required.",
        fix="Set a directory after the flag.",
        example="n3 package build --out dist",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="package build supports --out and --json.",
        fix="Remove the unsupported flag.",
        example="n3 package build --json",
    )


def _unexpected_arg_message(arg: str) -> str:
    return build_guidance_message(
        what=f"Unexpected argument '{arg}'.",
        why="package build does not accept positional arguments.",
        fix="Remove the argument or use --out.",
        example="n3 package build --out dist",
    )


def _print_usage() -> None:
    print("Usage:\n  n3 package build [--out DIR] [--json]")


__all__ = ["run_package_command"]
