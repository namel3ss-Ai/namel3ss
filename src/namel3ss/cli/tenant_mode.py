from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.federation.tenants import add_tenant, list_tenants, set_current_tenant


@dataclass(frozen=True)
class _TenantParams:
    subcommand: str
    app_arg: str | None
    json_mode: bool
    tenant_id: str | None = None
    name: str | None = None
    namespace_prefix: str | None = None
    storage_backend: str | None = None
    quotas: dict[str, float] | None = None


def run_tenant_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.subcommand == "help":
            _print_usage()
            return 0
        app_path = resolve_app_path(params.app_arg)
        project_root = app_path.parent
        if params.subcommand == "list":
            rows = list_tenants(project_root, app_path)
            payload = {"ok": True, "count": len(rows), "tenants": rows}
            return _emit(payload, json_mode=params.json_mode)
        if params.subcommand == "add":
            assert params.tenant_id and params.name and params.namespace_prefix and params.storage_backend
            path, entry = add_tenant(
                project_root=project_root,
                app_path=app_path,
                tenant_id=params.tenant_id,
                name=params.name,
                namespace_prefix=params.namespace_prefix,
                storage_backend=params.storage_backend,
                resource_quotas=params.quotas or {},
            )
            payload = {"ok": True, "tenants_path": path.as_posix(), "tenant": entry.to_dict()}
            return _emit(payload, json_mode=params.json_mode)
        if params.subcommand == "set-current":
            assert params.tenant_id
            path = set_current_tenant(project_root, app_path, params.tenant_id)
            payload = {"ok": True, "tenant_id": params.tenant_id, "current_tenant_path": path.as_posix()}
            return _emit(payload, json_mode=params.json_mode)
        raise Namel3ssError(_unknown_subcommand_message(params.subcommand))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _TenantParams:
    if not args or args[0] in {"help", "--help", "-h"}:
        return _TenantParams(subcommand="help", app_arg=None, json_mode=False)
    subcommand = str(args[0] or "").strip().lower()
    json_mode = False
    quotas: dict[str, float] = {}
    positional: list[str] = []

    idx = 1
    while idx < len(args):
        arg = args[idx]
        if arg == "--json":
            json_mode = True
            idx += 1
            continue
        if arg == "--quota":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_option_value_message("--quota"))
            key, value = _parse_quota(args[idx + 1])
            quotas[key] = value
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
        return _TenantParams(subcommand=subcommand, app_arg=app_arg, json_mode=json_mode)

    if subcommand == "add":
        if len(positional) < 4:
            raise Namel3ssError(_missing_add_args_message())
        app_arg = positional[4] if len(positional) >= 5 else None
        if len(positional) > 5:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return _TenantParams(
            subcommand=subcommand,
            app_arg=app_arg,
            json_mode=json_mode,
            tenant_id=positional[0],
            name=positional[1],
            namespace_prefix=positional[2],
            storage_backend=positional[3],
            quotas=quotas,
        )

    if subcommand == "set-current":
        if not positional:
            raise Namel3ssError(_missing_tenant_id_message(subcommand))
        tenant_id = positional[0]
        app_arg = positional[1] if len(positional) >= 2 else None
        if len(positional) > 2:
            raise Namel3ssError(_too_many_args_message(subcommand))
        return _TenantParams(
            subcommand=subcommand,
            app_arg=app_arg,
            json_mode=json_mode,
            tenant_id=tenant_id,
        )

    raise Namel3ssError(_unknown_subcommand_message(subcommand))


def _parse_quota(raw: str) -> tuple[str, float]:
    if "=" not in raw:
        raise Namel3ssError(
            build_guidance_message(
                what="Quota format is invalid.",
                why="Quota values must be key=value.",
                fix="Use --quota key=value.",
                example="--quota max_flows=100",
            )
        )
    key, value = raw.split("=", 1)
    name = key.strip()
    if not name:
        raise Namel3ssError(
            build_guidance_message(
                what="Quota key is missing.",
                why="Quota values must include a key.",
                fix="Set a quota key before '='.",
                example="--quota memory_gb=8",
            )
        )
    try:
        parsed = float(value)
    except Exception as err:
        raise Namel3ssError(_invalid_number_message("--quota", raw)) from err
    if parsed < 0:
        raise Namel3ssError(_invalid_number_message("--quota", raw))
    return name, parsed


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0 if bool(payload.get("ok")) else 1
    print("Tenants")
    print(f"  ok: {payload.get('ok')}")
    if "count" in payload:
        print(f"  count: {payload.get('count')}")
    if payload.get("tenants_path"):
        print(f"  tenants_path: {payload.get('tenants_path')}")
    if payload.get("current_tenant_path"):
        print(f"  current_tenant_path: {payload.get('current_tenant_path')}")
    if payload.get("tenant_id"):
        print(f"  tenant_id: {payload.get('tenant_id')}")
    tenant = payload.get("tenant")
    if isinstance(tenant, dict):
        print(f"  tenant: {tenant.get('tenant_id')} ({tenant.get('name')})")
    tenants = payload.get("tenants")
    if isinstance(tenants, list):
        for item in tenants:
            if not isinstance(item, dict):
                continue
            marker = " *" if bool(item.get("is_current")) else ""
            print(
                f"  - {item.get('tenant_id')} name={item.get('name')} "
                f"storage={item.get('storage_backend')}{marker}"
            )
    return 0 if bool(payload.get("ok")) else 1


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 tenant list [app.ai] [--json]\n"
        "  n3 tenant add <tenant_id> <name> <namespace_prefix> <storage_backend> [--quota key=value]... [app.ai] [--json]\n"
        "  n3 tenant set-current <tenant_id> [app.ai] [--json]"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown tenant command '{subcommand}'.",
        why="Supported commands are list, add, and set-current.",
        fix="Use one of the supported tenant commands.",
        example="n3 tenant list",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="Supported tenant flags are --quota and --json.",
        fix="Remove unsupported flags.",
        example="n3 tenant add acme \"ACME\" acme_ local --quota max_flows=100",
    )


def _missing_option_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Flag '{flag}' is missing a value.",
        why="This option requires a value.",
        fix="Provide a value after the flag.",
        example=f"n3 tenant add acme \"ACME\" acme_ local {flag} max_flows=100",
    )


def _too_many_args_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"tenant {subcommand} has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Pass at most one app.ai path.",
        example=f"n3 tenant {subcommand} app.ai",
    )


def _missing_add_args_message() -> str:
    return build_guidance_message(
        what="tenant add is missing required values.",
        why="add requires tenant_id, name, namespace_prefix, and storage_backend.",
        fix="Provide all required values in order.",
        example="n3 tenant add acme \"ACME Corp\" acme_ local",
    )


def _missing_tenant_id_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"tenant {subcommand} is missing tenant_id.",
        why="A tenant id is required.",
        fix="Provide tenant_id as the first positional argument.",
        example=f"n3 tenant {subcommand} acme",
    )


def _invalid_number_message(flag: str, value: str) -> str:
    return build_guidance_message(
        what=f"{flag} value '{value}' is invalid.",
        why="Expected a non-negative number.",
        fix="Provide a valid number.",
        example="--quota memory_gb=8",
    )


__all__ = ["run_tenant_command"]
