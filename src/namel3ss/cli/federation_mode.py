from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.federation.contracts import add_contract, list_contracts, remove_contract


@dataclass(frozen=True)
class _FederationParams:
    subcommand: str
    app_arg: str | None
    json_mode: bool
    source_tenant: str | None = None
    target_tenant: str | None = None
    flow_name: str | None = None
    input_schema: dict[str, str] | None = None
    output_schema: dict[str, str] | None = None
    auth: dict[str, str] | None = None
    rate_limit: int | None = None


def run_federation_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.subcommand == "help":
            _print_usage()
            return 0
        app_path = resolve_app_path(params.app_arg)
        project_root = app_path.parent
        if params.subcommand == "list":
            rows = list_contracts(project_root, app_path)
            payload = {"ok": True, "count": len(rows), "contracts": rows}
            return _emit(payload, json_mode=params.json_mode)
        if params.subcommand == "add-contract":
            assert params.source_tenant and params.target_tenant and params.flow_name
            path, contract = add_contract(
                project_root=project_root,
                app_path=app_path,
                source_tenant=params.source_tenant,
                target_tenant=params.target_tenant,
                flow_name=params.flow_name,
                input_schema=params.input_schema or {},
                output_schema=params.output_schema or {},
                auth=params.auth or {},
                rate_limit_calls_per_minute=params.rate_limit,
            )
            payload = {"ok": True, "federation_path": path.as_posix(), "contract": contract.to_dict()}
            return _emit(payload, json_mode=params.json_mode)
        if params.subcommand == "remove-contract":
            assert params.source_tenant and params.target_tenant and params.flow_name
            path, contract = remove_contract(
                project_root=project_root,
                app_path=app_path,
                source_tenant=params.source_tenant,
                target_tenant=params.target_tenant,
                flow_name=params.flow_name,
            )
            payload = {"ok": True, "federation_path": path.as_posix(), "contract": contract.to_dict()}
            return _emit(payload, json_mode=params.json_mode)
        raise Namel3ssError(_unknown_subcommand_message(params.subcommand))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _FederationParams:
    if not args or args[0] in {"help", "--help", "-h"}:
        return _FederationParams(subcommand="help", app_arg=None, json_mode=False)
    subcommand = str(args[0] or "").strip().lower()
    json_mode = False
    input_schema: dict[str, str] = {}
    output_schema: dict[str, str] = {}
    auth: dict[str, str] = {}
    rate_limit = None
    positional: list[str] = []

    idx = 1
    while idx < len(args):
        arg = args[idx]
        if arg == "--json":
            json_mode = True
            idx += 1
            continue
        if arg in {"--input", "--output", "--auth", "--rate-limit"}:
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_option_value_message(arg))
            value = args[idx + 1]
            if arg == "--input":
                input_schema.update(_parse_schema(value))
            elif arg == "--output":
                output_schema.update(_parse_schema(value))
            elif arg == "--auth":
                key, parsed = _parse_auth_pair(value)
                auth[key] = parsed
            elif arg == "--rate-limit":
                rate_limit = _parse_positive_int(value, flag=arg)
            idx += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
        idx += 1

    if subcommand == "list":
        app_arg = positional[0] if positional else None
        if len(positional) > 1:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return _FederationParams(subcommand=subcommand, app_arg=app_arg, json_mode=json_mode)

    if subcommand in {"add-contract", "remove-contract"}:
        if len(positional) < 3:
            raise Namel3ssError(_missing_contract_ref_message(subcommand))
        source_tenant = positional[0]
        target_tenant = positional[1]
        flow_name = positional[2]
        app_arg = positional[3] if len(positional) >= 4 else None
        if len(positional) > 4:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return _FederationParams(
            subcommand=subcommand,
            app_arg=app_arg,
            json_mode=json_mode,
            source_tenant=source_tenant,
            target_tenant=target_tenant,
            flow_name=flow_name,
            input_schema=input_schema,
            output_schema=output_schema,
            auth=auth,
            rate_limit=rate_limit,
        )

    raise Namel3ssError(_unknown_subcommand_message(subcommand))


def _parse_schema(raw: str) -> dict[str, str]:
    text = str(raw or "").strip()
    if not text:
        return {}
    values: dict[str, str] = {}
    for part in text.split(","):
        chunk = part.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise Namel3ssError(
                build_guidance_message(
                    what="Schema format is invalid.",
                    why="Schema entries must use field:type.",
                    fix="Use comma-separated field:type values.",
                    example="--input customer_id:number,name:text",
                )
            )
        field, type_name = chunk.split(":", 1)
        name = field.strip()
        type_text = type_name.strip()
        if not name or not type_text:
            raise Namel3ssError(
                build_guidance_message(
                    what="Schema entry is invalid.",
                    why="Each schema entry needs both field and type.",
                    fix="Provide field:type pairs.",
                    example="--output info:text",
                )
            )
        values[name] = type_text
    return values


def _parse_auth_pair(raw: str) -> tuple[str, str]:
    if "=" not in raw:
        raise Namel3ssError(
            build_guidance_message(
                what="Auth format is invalid.",
                why="Auth entries must use key=value.",
                fix="Use --auth key=value.",
                example="--auth token=abcdef123",
            )
        )
    key, value = raw.split("=", 1)
    name = key.strip()
    if not name:
        raise Namel3ssError(
            build_guidance_message(
                what="Auth key is missing.",
                why="Auth entries need a key before '='.",
                fix="Provide an auth key.",
                example="--auth client_id=acme_beta_client",
            )
        )
    return name, value.strip()


def _parse_positive_int(value: str, *, flag: str) -> int:
    try:
        parsed = int(value)
    except Exception as err:
        raise Namel3ssError(_invalid_number_message(flag, value)) from err
    if parsed <= 0:
        raise Namel3ssError(_invalid_number_message(flag, value))
    return parsed


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0 if bool(payload.get("ok")) else 1
    print("Federation")
    print(f"  ok: {payload.get('ok')}")
    if "count" in payload:
        print(f"  count: {payload.get('count')}")
    if payload.get("federation_path"):
        print(f"  federation_path: {payload.get('federation_path')}")
    contract = payload.get("contract")
    if isinstance(contract, dict):
        source = contract.get("source_tenant")
        target = contract.get("target_tenant")
        flow = contract.get("flow_name")
        print(f"  contract: {source}->{target}:{flow}")
    rows = payload.get("contracts")
    if isinstance(rows, list):
        for item in rows:
            if not isinstance(item, dict):
                continue
            print(f"  - {item.get('source_tenant')}->{item.get('target_tenant')}:{item.get('flow_name')}")
    return 0 if bool(payload.get("ok")) else 1


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 federation list [app.ai] [--json]\n"
        "  n3 federation add-contract <source_tenant> <target_tenant> <flow_name> [--input field:type[,field:type]] [--output field:type[,field:type]] [--auth key=value]... [--rate-limit N] [app.ai] [--json]\n"
        "  n3 federation remove-contract <source_tenant> <target_tenant> <flow_name> [app.ai] [--json]"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown federation command '{subcommand}'.",
        why="Supported commands are list, add-contract, and remove-contract.",
        fix="Use one of the supported federation commands.",
        example="n3 federation list",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="Supported federation flags are --input, --output, --auth, --rate-limit, and --json.",
        fix="Remove unsupported flags.",
        example="n3 federation add-contract acme beta get_customer_info --rate-limit 60",
    )


def _missing_option_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Flag '{flag}' is missing a value.",
        why="This option requires a value.",
        fix="Provide a value after the flag.",
        example=f"n3 federation add-contract acme beta get_customer_info {flag} value",
    )


def _missing_contract_ref_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"federation {subcommand} is missing values.",
        why="You must provide source_tenant, target_tenant, and flow_name.",
        fix="Provide all required positional arguments in order.",
        example=f"n3 federation {subcommand} acme beta get_customer_info",
    )


def _too_many_args_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"federation {subcommand} has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Pass at most one app.ai path.",
        example=f"n3 federation {subcommand} app.ai",
    )


def _invalid_number_message(flag: str, value: str) -> str:
    return build_guidance_message(
        what=f"{flag} value '{value}' is invalid.",
        why="Expected a positive integer.",
        fix="Provide a valid integer.",
        example="--rate-limit 60",
    )


__all__ = ["run_federation_command"]
