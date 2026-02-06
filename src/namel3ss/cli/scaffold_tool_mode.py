from __future__ import annotations

import json
from pathlib import Path
import re
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.module_loader import load_project


def run_scaffold_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params["subcommand"] == "help":
            _print_usage()
            return 0
        if params["subcommand"] != "test":
            raise Namel3ssError(_unknown_subcommand_message(str(params["subcommand"])))

        app_path = resolve_app_path(params["app_arg"])
        project = load_project(app_path)
        flow_name = str(params["flow_name"])
        contract = _find_contract(project.app_ast.contracts, flow_name)
        sample_input = _sample_input(contract)

        tests_dir = app_path.parent / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        safe_name = _safe_name(flow_name)
        output_path = tests_dir / f"test_{safe_name}_generated.py"
        output_path.write_text(_render_test(flow_name, sample_input), encoding="utf-8")

        payload = {
            "ok": True,
            "flow": flow_name,
            "path": output_path.as_posix(),
            "sample_input": sample_input,
        }
        if bool(params["json_mode"]):
            print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
            return 0
        print(f"Generated {output_path}")
        return 0
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> dict[str, object]:
    if not args or args[0] in {"help", "-h", "--help"}:
        return {"subcommand": "help", "flow_name": None, "json_mode": False, "app_arg": None}
    subcommand = args[0].strip().lower()
    json_mode = False
    positional: list[str] = []
    i = 1
    while i < len(args):
        token = args[i]
        if token == "--json":
            json_mode = True
            i += 1
            continue
        if token.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(token))
        positional.append(token)
        i += 1
    if subcommand == "test":
        if not positional:
            raise Namel3ssError(_missing_flow_message())
        if len(positional) > 2:
            raise Namel3ssError(_too_many_args_message())
        return {
            "subcommand": subcommand,
            "flow_name": positional[0],
            "app_arg": positional[1] if len(positional) > 1 else None,
            "json_mode": json_mode,
        }
    raise Namel3ssError(_unknown_subcommand_message(subcommand))


def _find_contract(contracts, flow_name: str):  # noqa: ANN001
    for contract in contracts:
        if getattr(contract, "kind", "") == "flow" and getattr(contract, "name", "") == flow_name:
            return contract
    raise Namel3ssError(_missing_contract_message(flow_name))


def _sample_input(contract) -> dict[str, object]:  # noqa: ANN001
    signature = getattr(contract, "signature", None)
    inputs = getattr(signature, "inputs", None) or []
    payload: dict[str, object] = {}
    for param in inputs:
        name = str(getattr(param, "name", "")).strip()
        type_name = str(getattr(param, "type_name", "text")).strip().lower()
        if not name:
            continue
        payload[name] = _sample_value(type_name)
    return payload


def _sample_value(type_name: str) -> object:
    if "number" in type_name or type_name in {"int", "integer"}:
        return 0
    if "boolean" in type_name or type_name == "bool":
        return True
    if type_name.startswith("list"):
        return []
    if type_name.startswith("map") or type_name == "json":
        return {}
    if "null" in type_name:
        return None
    return "sample"


def _render_test(flow_name: str, sample_input: dict[str, object]) -> str:
    slug = _safe_name(flow_name)
    input_literal = json.dumps(sample_input, sort_keys=True)
    return (
        "from __future__ import annotations\n\n"
        "from pathlib import Path\n\n"
        "from namel3ss.module_loader import load_project\n"
        "from namel3ss.runtime.run_pipeline import build_flow_payload\n\n"
        f"def test_{slug}_generated_flow() -> None:\n"
        '    app_path = Path(__file__).resolve().parents[1] / "app.ai"\n'
        "    project = load_project(app_path)\n"
        f"    outcome = build_flow_payload(project.program, \"{flow_name}\", input={input_literal})\n"
        '    assert outcome.payload.get("ok") is True\n'
    )


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")
    return cleaned.lower() or "flow"


def _print_usage() -> None:
    print("Usage:\n  n3 scaffold test <flow_name> [app.ai] [--json]")


def _missing_flow_message() -> str:
    return build_guidance_message(
        what="scaffold test needs a flow name.",
        why="The generator creates one test per target flow.",
        fix="Pass the flow name as the first argument.",
        example="n3 scaffold test hello",
    )


def _missing_contract_message(flow_name: str) -> str:
    return build_guidance_message(
        what=f"Flow '{flow_name}' is missing a contract.",
        why="Test scaffolding needs input fields from the contract.",
        fix="Add a contract flow block for this flow.",
        example=f'contract flow "{flow_name}":\n  input:\n    value is text\n  output:\n    result is text',
    )


def _too_many_args_message() -> str:
    return build_guidance_message(
        what="Too many arguments for scaffold test.",
        why="Only flow name and optional app path are supported.",
        fix="Remove extra positional arguments.",
        example="n3 scaffold test hello app.ai",
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown scaffold command '{subcommand}'.",
        why="Supported scaffold commands: test.",
        fix="Run n3 scaffold help.",
        example="n3 scaffold test hello",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="scaffold supports --json only.",
        fix="Remove unsupported flags.",
        example="n3 scaffold test hello --json",
    )


__all__ = ["run_scaffold_command"]
