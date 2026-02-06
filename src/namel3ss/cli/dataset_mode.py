from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.datasets import add_dataset_version, dataset_history, load_dataset_registry, parse_schema_arg
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error


@dataclass(frozen=True)
class _Params:
    subcommand: str
    app_arg: str | None
    json_mode: bool
    dataset_name: str | None = None
    version: str | None = None
    source: str | None = None
    schema_arg: str | None = None
    transforms: tuple[str, ...] = ()
    owner: str | None = None


def run_dataset_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        if params.subcommand == "help":
            _print_usage()
            return 0

        app_path = resolve_app_path(params.app_arg)
        project_root = app_path.parent

        if params.subcommand == "list":
            registry = load_dataset_registry(project_root, app_path)
            datasets = []
            for dataset in registry.sorted_datasets():
                versions = list(dataset.sorted_versions())
                latest = versions[-1].version if versions else None
                datasets.append(
                    {
                        "name": dataset.name,
                        "version_count": len(versions),
                        "latest_version": latest,
                    }
                )
            payload = {
                "ok": True,
                "count": len(datasets),
                "datasets": datasets,
            }
            return _emit(payload, json_mode=params.json_mode)

        if params.subcommand == "history":
            assert params.dataset_name
            versions = dataset_history(project_root=project_root, app_path=app_path, dataset_name=params.dataset_name)
            payload = {
                "ok": True,
                "dataset_name": params.dataset_name,
                "count": len(versions),
                "versions": [entry.to_dict() for entry in versions],
            }
            return _emit(payload, json_mode=params.json_mode)

        if params.subcommand == "add-version":
            assert params.dataset_name and params.version
            schema = parse_schema_arg(params.schema_arg or "")
            path, entry = add_dataset_version(
                project_root=project_root,
                app_path=app_path,
                dataset_name=params.dataset_name,
                version=params.version,
                schema=schema,
                source=params.source or "",
                transformations=list(params.transforms),
                owner=params.owner,
            )
            payload = {
                "ok": True,
                "dataset_registry_path": path.as_posix(),
                "dataset_name": entry.dataset_name,
                "version": entry.version,
                "source": entry.source,
                "schema": {field: type_name for field, type_name in entry.schema},
                "transformations": list(entry.transformations),
                "owner": entry.owner,
            }
            return _emit(payload, json_mode=params.json_mode)

        raise Namel3ssError(_unknown_subcommand_message(params.subcommand))
    except Namel3ssError as err:
        print(prepare_cli_text(format_error(err, None)), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _Params:
    if not args or args[0] in {"help", "-h", "--help"}:
        return _Params(subcommand="help", app_arg=None, json_mode=False)

    subcommand = str(args[0]).strip().lower()
    json_mode = False
    source = None
    schema_arg = None
    owner = None
    transforms: list[str] = []
    positional: list[str] = []

    i = 1
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg in {"--source", "--schema", "--owner", "--transform"}:
            if i + 1 >= len(args):
                raise Namel3ssError(_missing_option_value_message(arg))
            value = args[i + 1]
            if arg == "--source":
                source = value
            elif arg == "--schema":
                schema_arg = value
            elif arg == "--owner":
                owner = value
            else:
                transforms.append(value)
            i += 2
            continue
        if arg.startswith("--"):
            raise Namel3ssError(_unknown_flag_message(arg))
        positional.append(arg)
        i += 1

    if subcommand == "list":
        app_arg = positional[0] if positional else None
        if len(positional) > 1:
            raise Namel3ssError(_too_many_args_message("list"))
        return _Params(subcommand=subcommand, app_arg=app_arg, json_mode=json_mode)

    if subcommand == "history":
        if len(positional) < 1:
            raise Namel3ssError(_missing_dataset_message("history"))
        dataset_name = positional[0]
        app_arg = positional[1] if len(positional) >= 2 else None
        if len(positional) > 2:
            raise Namel3ssError(_too_many_args_message("history"))
        return _Params(
            subcommand=subcommand,
            app_arg=app_arg,
            json_mode=json_mode,
            dataset_name=dataset_name,
        )

    if subcommand == "add-version":
        if len(positional) < 2:
            raise Namel3ssError(_missing_dataset_message("add-version"))
        dataset_name = positional[0]
        version = positional[1]
        app_arg = positional[2] if len(positional) >= 3 else None
        if len(positional) > 3:
            raise Namel3ssError(_too_many_args_message("add-version"))
        missing: list[str] = []
        if source is None:
            missing.append("--source")
        if schema_arg is None:
            missing.append("--schema")
        if missing:
            raise Namel3ssError(_missing_required_flags_message(missing))
        return _Params(
            subcommand=subcommand,
            app_arg=app_arg,
            json_mode=json_mode,
            dataset_name=dataset_name,
            version=version,
            source=source,
            schema_arg=schema_arg,
            transforms=tuple(transforms),
            owner=owner,
        )

    raise Namel3ssError(_unknown_subcommand_message(subcommand))


def _emit(payload: dict[str, object], *, json_mode: bool) -> int:
    if json_mode:
        print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
        return 0 if bool(payload.get("ok")) else 1
    print("Datasets")
    print(f"  ok: {payload.get('ok')}")
    if "count" in payload:
        print(f"  count: {payload.get('count')}")
    if "dataset_registry_path" in payload:
        print(f"  dataset_registry_path: {payload.get('dataset_registry_path')}")
    if payload.get("dataset_name"):
        print(f"  dataset: {payload.get('dataset_name')}")
    if payload.get("version"):
        print(f"  version: {payload.get('version')}")
    datasets = payload.get("datasets")
    if isinstance(datasets, list):
        for item in datasets:
            if not isinstance(item, dict):
                continue
            print(f"  - {item.get('name')} versions={item.get('version_count')} latest={item.get('latest_version')}")
    versions = payload.get("versions")
    if isinstance(versions, list):
        for item in versions:
            if not isinstance(item, dict):
                continue
            print(f"  - version={item.get('version')} source={item.get('source')}")
    return 0 if bool(payload.get("ok")) else 1


def _print_usage() -> None:
    print(
        "Usage:\n"
        "  n3 dataset list [app.ai] [--json]\n"
        "  n3 dataset history <dataset_name> [app.ai] [--json]\n"
        "  n3 dataset add-version <dataset_name> <version> --source SOURCE --schema field:type[,field:type] [--transform NOTE]... [--owner OWNER] [app.ai] [--json]"
    )


def _unknown_subcommand_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"Unknown dataset command '{subcommand}'.",
        why="Supported commands are list, history, and add-version.",
        fix="Use one of the supported subcommands.",
        example="n3 dataset list",
    )


def _unknown_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Unknown flag '{flag}'.",
        why="This flag is not supported for dataset commands.",
        fix="Remove the unsupported flag.",
        example="n3 dataset list",
    )


def _missing_option_value_message(flag: str) -> str:
    return build_guidance_message(
        what=f"Flag '{flag}' is missing a value.",
        why="This option requires a value.",
        fix="Provide a value after the flag.",
        example=f"n3 dataset add-version faq-dataset 1.0.0 {flag} value",
    )


def _missing_dataset_message(subcommand: str) -> str:
    if subcommand == "history":
        return build_guidance_message(
            what="dataset history is missing dataset name.",
            why="history needs the dataset name.",
            fix="Provide the dataset name.",
            example="n3 dataset history faq-dataset",
        )
    return build_guidance_message(
        what="dataset add-version is missing arguments.",
        why="add-version needs dataset name and semantic version.",
        fix="Provide dataset name and version.",
        example="n3 dataset add-version faq-dataset 1.0.0 --source upload_1 --schema question:text,answer:text",
    )


def _missing_required_flags_message(flags: list[str]) -> str:
    joined = ", ".join(flags)
    return build_guidance_message(
        what="dataset add-version is missing required flags.",
        why=f"The following flags are required: {joined}.",
        fix="Provide all required flags.",
        example="n3 dataset add-version faq-dataset 1.0.0 --source upload_1 --schema question:text,answer:text",
    )


def _too_many_args_message(subcommand: str) -> str:
    return build_guidance_message(
        what=f"dataset {subcommand} has too many positional arguments.",
        why="Only one optional app path is supported.",
        fix="Remove extra positional values.",
        example=f"n3 dataset {subcommand} demo app.ai",
    )


__all__ = ["run_dataset_command"]
