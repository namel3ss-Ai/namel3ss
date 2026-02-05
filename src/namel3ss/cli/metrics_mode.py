from __future__ import annotations

from dataclasses import dataclass
import sys

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.text_output import prepare_cli_text
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.render import format_error
from namel3ss.observability.ai_metrics import apply_thresholds, load_ai_metrics, load_thresholds, summarize_ai_metrics


@dataclass(frozen=True)
class _MetricsParams:
    app_arg: str | None
    json_mode: bool


def run_metrics_command(args: list[str]) -> int:
    try:
        params = _parse_args(args)
        app_path = resolve_app_path(params.app_arg)
        records = load_ai_metrics(app_path.parent, app_path)
        summary = summarize_ai_metrics(records)
        thresholds = load_thresholds(app_path.parent, app_path)
        drift = apply_thresholds(summary, thresholds)
        payload = {"summary": summary, "thresholds": drift}
        if params.json_mode:
            print(canonical_json_dumps(payload, pretty=True, drop_run_keys=False))
            return 0
        _print_human(payload)
        return 0
    except Namel3ssError as err:
        message = format_error(err, None)
        print(prepare_cli_text(message), file=sys.stderr)
        return 1


def _parse_args(args: list[str]) -> _MetricsParams:
    app_arg = None
    json_mode = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="metrics supports --json only.",
                    fix="Remove the unsupported flag.",
                    example="n3 metrics --json",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="metrics accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 metrics app.ai",
            )
        )
    return _MetricsParams(app_arg=app_arg, json_mode=json_mode)


def _print_human(payload: dict) -> None:
    summary = payload.get("summary") or {}
    thresholds = payload.get("thresholds") or []
    print("AI metrics")
    if isinstance(summary, dict):
        for key in sorted(summary.keys()):
            print(f"  {key}: {summary[key]}")
    if thresholds:
        print("Thresholds")
        for entry in thresholds:
            metric = entry.get("metric")
            value = entry.get("value")
            threshold = entry.get("threshold")
            drifted = entry.get("drifted")
            print(f"  {metric}: {value} (threshold {threshold}) drifted={drifted}")


__all__ = ["run_metrics_command"]
