from __future__ import annotations

import csv
import json
from pathlib import Path

from namel3ss.determinism import canonical_json_dump, canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.models import resolve_model_entry
from namel3ss.module_loader import load_project
from namel3ss.runtime.ai.providers.mock import MockProvider
from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.persistence_paths import resolve_persistence_root


DEFAULT_AI_EVAL_DIR = Path(".namel3ss") / "observability" / "evals" / "ai"
AI_EVAL_FILENAME = "flow_eval.json"

_ALLOWED_METRICS = {"accuracy", "precision", "recall", "f1", "f1_score", "rouge", "bleu", "exact_match"}


def run_ai_flow_eval(
    *,
    flow_name: str,
    app_path: Path,
    out_dir: Path | None = None,
) -> dict[str, object]:
    project = load_project(app_path)
    program = project.program
    ai_flow = _find_ai_flow(program, flow_name)
    tests = getattr(ai_flow, "tests", None)
    if tests is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f'AI flow "{flow_name}" has no tests block.',
                why="n3 eval flow needs dataset and metrics in the tests block.",
                fix="Add tests with dataset and metrics to the AI flow.",
                example='tests:\n  dataset is "qa_examples.json"\n  metrics:\n    - accuracy',
            )
        )
    dataset_path = _resolve_dataset_path(app_path, tests.dataset)
    cases = _load_cases(dataset_path)
    if not cases:
        raise Namel3ssError(f"Dataset {dataset_path.as_posix()} has no cases.")
    metrics = _normalize_metrics(tests.metrics)
    provider = MockProvider()

    evaluated_cases: list[dict[str, object]] = []
    for index, case in enumerate(cases):
        input_payload = case["input"]
        expected = case.get("expected")
        result = execute_program_flow(
            program,
            flow_name,
            state={},
            input=input_payload if isinstance(input_payload, dict) else {"value": input_payload},
            ai_provider=provider,
        )
        predicted = _extract_prediction(result.last_value)
        evaluated_cases.append(
            {
                "index": index + 1,
                "input": input_payload,
                "expected": expected,
                "predicted": predicted,
            }
        )

    summary = _compute_metrics(evaluated_cases, metrics=metrics)
    model_name = str(getattr(ai_flow, "model", "") or "")
    model_entry = resolve_model_entry(
        project_root=getattr(program, "project_root", None),
        app_path=getattr(program, "app_path", None),
        reference=model_name,
    )
    model_version = model_entry.version if model_entry is not None else "unknown"
    payload = {
        "flow_name": flow_name,
        "model": model_name,
        "model_version": model_version,
        "dataset": tests.dataset,
        "metrics": metrics,
        "results": summary,
        "cases": evaluated_cases,
    }
    target_dir = out_dir or _default_out_dir(program, flow_name, model_version=model_version)
    target_dir.mkdir(parents=True, exist_ok=True)
    canonical_json_dump(target_dir / AI_EVAL_FILENAME, payload, pretty=True)
    return payload


def load_ai_flow_evals(project_root: Path | str | None, app_path: Path | str | None) -> list[dict]:
    root = resolve_persistence_root(project_root, app_path, allow_create=False)
    if root is None:
        return []
    base = Path(root) / DEFAULT_AI_EVAL_DIR
    if not base.exists():
        return []
    entries: list[dict] = []
    for path in sorted(base.rglob(AI_EVAL_FILENAME)):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def _find_ai_flow(program, flow_name: str):
    for flow in getattr(program, "ai_flows", []) or []:
        if flow.name == flow_name:
            return flow
    raise Namel3ssError(
        build_guidance_message(
            what=f'AI flow "{flow_name}" was not found.',
            why="n3 eval flow only works with named AI flows.",
            fix="Use an AI flow name from your app.",
            example='n3 eval flow "answer_question"',
        )
    )


def _resolve_dataset_path(app_path: Path, dataset_name: str) -> Path:
    raw = str(dataset_name or "").strip()
    if not raw:
        raise Namel3ssError("Dataset path is empty.")
    dataset_path = Path(raw)
    if not dataset_path.is_absolute():
        dataset_path = app_path.parent / dataset_path
    if not dataset_path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Dataset not found: {dataset_path.as_posix()}",
                why="tests dataset must point to an existing file.",
                fix="Create the dataset file or fix the path.",
                example='dataset is "qa_examples.json"',
            )
        )
    return dataset_path


def _load_cases(path: Path) -> list[dict[str, object]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _normalize_cases(payload)
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        return _normalize_cases(rows)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    return [{"input": text}]


def _normalize_cases(payload: object) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("cases"), list):
            payload = payload["cases"]
        else:
            payload = [payload]
    if not isinstance(payload, list):
        payload = [payload]
    for item in payload:
        if isinstance(item, dict):
            if "input" in item:
                cases.append({"input": item.get("input"), "expected": item.get("expected")})
            else:
                expected = item.get("expected") if isinstance(item.get("expected"), (str, int, float, bool)) else None
                input_payload = {k: v for k, v in item.items() if k != "expected"}
                cases.append({"input": input_payload, "expected": expected})
            continue
        cases.append({"input": item})
    return cases


def _normalize_metrics(raw_metrics: list[str]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for metric in raw_metrics:
        value = str(metric or "").strip().lower()
        if not value:
            continue
        if value in seen:
            continue
        if value not in _ALLOWED_METRICS:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Unsupported metric "{value}".',
                    why="Only deterministic metrics are supported.",
                    fix="Use accuracy, precision, recall, f1, f1_score, rouge, bleu, or exact_match.",
                    example="metrics:\n  - accuracy\n  - exact_match",
                )
            )
        seen.add(value)
        values.append(value)
    if not values:
        raise Namel3ssError("No valid metrics were provided.")
    return values


def _extract_prediction(value: object) -> str:
    if isinstance(value, dict):
        for key in ("ans", "answer", "result", "output", "value"):
            if key in value:
                return _extract_prediction(value[key])
        return canonical_json_dumps(value, pretty=False, drop_run_keys=False)
    if value is None:
        return ""
    return str(value)


def _compute_metrics(cases: list[dict[str, object]], *, metrics: list[str]) -> dict[str, float]:
    total = len(cases)
    comparable = 0
    matches = 0
    token_overlap_total = 0.0
    for case in cases:
        has_expected = case.get("expected") is not None
        expected = _normalize_text(case.get("expected"))
        predicted = _normalize_text(case.get("predicted"))
        if has_expected:
            comparable += 1
            if predicted == expected:
                matches += 1
            token_overlap_total += _token_overlap(predicted, expected)
    metric_total = comparable if comparable else total
    accuracy = (matches / metric_total) if metric_total else 0.0
    rouge = (token_overlap_total / metric_total) if metric_total else 0.0
    results: dict[str, float] = {}
    for metric in metrics:
        if metric in {"accuracy", "exact_match"}:
            results[metric] = accuracy
            continue
        if metric in {"precision", "recall", "f1", "f1_score"}:
            results[metric] = accuracy
            continue
        if metric in {"rouge", "bleu"}:
            results[metric] = rouge
            continue
    return results


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _token_overlap(left: str, right: str) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / float(len(left_tokens | right_tokens))


def _default_out_dir(program, flow_name: str, *, model_version: str) -> Path:
    root = resolve_persistence_root(getattr(program, "project_root", None), getattr(program, "app_path", None), allow_create=True)
    safe_flow = flow_name.replace(" ", "_")
    safe_version = model_version.replace(" ", "_")
    return Path(root) / DEFAULT_AI_EVAL_DIR / safe_flow / safe_version


__all__ = ["AI_EVAL_FILENAME", "DEFAULT_AI_EVAL_DIR", "load_ai_flow_evals", "run_ai_flow_eval"]
