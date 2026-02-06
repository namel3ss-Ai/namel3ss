from __future__ import annotations

from pathlib import Path
import sys

from namel3ss.cli.scaffold_mode import EXAMPLES, TEMPLATES, run_new
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.cli.text_output import prepare_cli_text


DEFAULT_APP = 'spec is "1.0"\n\nflow "hello": purity is "pure"\n  return "ok"\n'
DEFAULT_MODELS = (
    "models:\n"
    "  default:\n"
    "    version: 1.0.0\n"
    "    provider: mock\n"
    "    status: active\n"
)
DEFAULT_DATASETS = (
    "datasets:\n"
    "  - name: sample_dataset\n"
    "    versions:\n"
    "      - version: 1.0.0\n"
    "        schema:\n"
    "          text: text\n"
    "        source: seed\n"
)


def run_init_command(args: list[str]) -> int:
    try:
        if _looks_like_template_init(args):
            return run_new(args)
        params = _parse_args(args)
        if params["help"]:
            _print_usage()
            return 0
        project_name = str(params["project_name"])
        force = bool(params["force"])
        json_mode = bool(params["json_mode"])

        root = (Path.cwd() / project_name).resolve()
        if root.exists() and not force:
            raise Namel3ssError(_target_exists_message(root))

        root.mkdir(parents=True, exist_ok=True)
        created = _write_project_files(root)

        payload = {
            "ok": True,
            "project": project_name,
            "path": root.as_posix(),
            "files": [path.as_posix() for path in created],
            "force": force,
        }
        if json_mode:
            print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
            return 0

        print(f"Created project at {root}")
        print("Files")
        for file_path in created:
            print(f"  - {file_path.relative_to(root).as_posix()}")
        return 0
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _write_project_files(root: Path) -> list[Path]:
    files: dict[str, str] = {
        "app.ai": DEFAULT_APP,
        "models.yaml": DEFAULT_MODELS,
        "dataset_registry.yaml": DEFAULT_DATASETS,
        "README.md": _readme(root.name),
    }
    created: list[Path] = []
    for relative in sorted(files.keys()):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[relative], encoding="utf-8")
        created.append(path)
    (root / ".namel3ss").mkdir(parents=True, exist_ok=True)
    return created


def _readme(project_name: str) -> str:
    return (
        f"# {project_name}\n\n"
        "Starter namel3ss project.\n\n"
        "## Run\n\n"
        "`n3 run app.ai`\n"
    )


def _parse_args(args: list[str]) -> dict[str, object]:
    if not args or args[0] in {"help", "-h", "--help"}:
        return {"help": True, "project_name": None, "force": False, "json_mode": False}
    force = False
    json_mode = False
    positional: list[str] = []
    for token in args:
        if token == "--force":
            force = True
            continue
        if token == "--json":
            json_mode = True
            continue
        if token.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(token))
        positional.append(token)
    if len(positional) != 1:
        raise Namel3ssError(_usage_message())
    return {
        "help": False,
        "project_name": positional[0].strip(),
        "force": force,
        "json_mode": json_mode,
    }


def _usage_message() -> str:
    return build_guidance_message(
        what="init requires exactly one project name.",
        why="The command creates one deterministic project directory.",
        fix="Pass a single project name.",
        example="n3 init hello_app",
    )


def _target_exists_message(path: Path) -> str:
    return build_guidance_message(
        what=f"Target directory already exists: {path.as_posix()}.",
        why="init does not overwrite existing work by default.",
        fix="Use --force or choose a new project name.",
        example="n3 init hello_app --force",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="init supports --force and --json only.",
        fix="Remove the unsupported flag.",
        example="n3 init hello_app --json",
    )


def _looks_like_template_init(args: list[str]) -> bool:
    if not args:
        return False
    command = args[0].strip().lower()
    if command in {"pkg", "package", "example", "examples"}:
        return True
    template_names = {spec.name for spec in TEMPLATES}
    example_names = {spec.name for spec in EXAMPLES}
    if command in template_names or command in example_names:
        return True
    return False


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 init <project_name> [--force] [--json]\n"
        "  n3 init <template> <name>            # legacy template scaffold"
    )


__all__ = ["run_init_command"]
