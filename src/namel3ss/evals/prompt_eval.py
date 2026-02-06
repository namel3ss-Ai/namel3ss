from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re

from namel3ss.cli.app_loader import load_program
from namel3ss.config.loader import load_config
from namel3ss.determinism import canonical_json_dumps, canonical_json_dump
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.ai.providers.registry import get_provider
from namel3ss.runtime.persistence_paths import resolve_persistence_root


EVALS_DIRNAME = "evals"
PROMPT_EVAL_FILENAME = "prompt_eval.json"


def run_prompt_eval(
    *,
    prompt_name: str,
    input_path: Path,
    app_path: Path,
    out_dir: Path | None = None,
) -> dict:
    program, _ = load_program(app_path.as_posix())
    prompt = _find_prompt(program, prompt_name)
    cases = _load_cases(input_path)
    config = load_config(app_path=app_path, root=app_path.parent)
    provider = get_provider(config.answer.provider, config)
    model = config.answer.model
    results = []
    for case in cases:
        input_value = case.get("input")
        expected = case.get("expected")
        prompt_text = _render_prompt_text(prompt["text"], input_value)
        user_input = _render_input(input_value)
        response = provider.ask(
            model=model,
            system_prompt=prompt_text,
            user_input=user_input,
            tools=[],
            memory=None,
            tool_results=None,
        )
        output_text = getattr(response, "output", response)
        output_text = str(output_text)
        metrics = _evaluate_output(output_text, expected)
        record = {
            "prompt_name": prompt["name"],
            "input_id": _input_id(input_value),
            "output": output_text,
            "metrics": metrics,
        }
        if expected is not None:
            record["expected"] = expected
        results.append(record)
    summary = _summarize_metrics(results)
    payload = {
        "prompt": {
            "name": prompt["name"],
            "version": prompt["version"],
            "description": prompt.get("description"),
        },
        "cases": results,
        "summary": summary,
    }
    _write_eval_payload(payload, out_dir or _default_eval_dir(app_path, prompt["name"]))
    return payload


def load_prompt_evals(project_root: Path | None, app_path: Path | None) -> list[dict]:
    root = resolve_persistence_root(project_root, app_path, allow_create=False)
    if root is None:
        return []
    eval_root = Path(root) / ".namel3ss" / "observability" / EVALS_DIRNAME
    if not eval_root.exists():
        return []
    entries: list[dict] = []
    for path in sorted(eval_root.rglob(PROMPT_EVAL_FILENAME)):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def _find_prompt(program, prompt_name: str) -> dict:
    for prompt in getattr(program, "prompts", []) or []:
        if prompt.name == prompt_name:
            return {
                "name": prompt.name,
                "version": prompt.version,
                "text": prompt.text,
                "description": prompt.description,
            }
    raise Namel3ssError(
        build_guidance_message(
            what=f'Prompt "{prompt_name}" was not found.',
            why="The prompt name must match a prompt declaration.",
            fix="Check the prompt name in app.ai.",
            example='prompt "summary_prompt":',
        )
    )


def _load_cases(path: Path) -> list[dict]:
    if not path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Input file not found: {path}.",
                why="Prompt evaluation needs an input file.",
                fix="Provide a valid file path.",
                example="n3 eval prompt summary_prompt --input samples.json",
            )
        )
    if path.suffix.lower() == ".json":
        return _load_json_cases(path)
    if path.suffix.lower() == ".csv":
        return _load_csv_cases(path)
    text = path.read_text(encoding="utf-8").strip()
    return [{"input": text}]


def _load_json_cases(path: Path) -> list[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Input JSON is invalid.",
                why="Prompt evaluation expects valid JSON.",
                fix="Fix the JSON file contents.",
                example='{"input": "hello"}',
            )
        ) from err
    if isinstance(payload, list):
        return [_normalize_case(item) for item in payload]
    if isinstance(payload, dict):
        if isinstance(payload.get("cases"), list):
            return [_normalize_case(item) for item in payload.get("cases")]
        if "input" in payload:
            return [_normalize_case(payload)]
        return [{"input": payload}]
    return [{"input": str(payload)}]


def _load_csv_cases(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    cases = []
    for row in rows:
        if "input" in row:
            case = {"input": row.get("input")}
            if "expected" in row:
                case["expected"] = row.get("expected")
            cases.append(case)
        else:
            cases.append({"input": row})
    return cases


def _normalize_case(value: object) -> dict:
    if isinstance(value, dict):
        if "input" in value:
            return {"input": value.get("input"), "expected": value.get("expected")}
        return {"input": value}
    return {"input": value}


def _render_prompt_text(prompt_text: str, input_value: object) -> str:
    text = str(prompt_text or "")
    if "{input}" in text:
        text = text.replace("{input}", _render_input(input_value))
    if isinstance(input_value, dict):
        def _replace(match):
            key = match.group(1)
            return str(input_value.get(key, ""))
        text = re.sub(r"\{input\.([A-Za-z0-9_]+)\}", _replace, text)
    return text


def _render_input(input_value: object) -> str:
    if isinstance(input_value, str):
        return input_value
    return canonical_json_dumps(input_value, pretty=False, drop_run_keys=False)


def _evaluate_output(output_text: str, expected: object | None) -> dict:
    metrics: dict[str, float] = {}
    if expected is None:
        return metrics
    expected_text = str(expected)
    output_clean = output_text.strip()
    expected_clean = expected_text.strip()
    metrics["accuracy"] = 1.0 if output_clean == expected_clean else 0.0
    metrics["similarity"] = _similarity(output_clean, expected_clean)
    return metrics


def _similarity(left: str, right: str) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    left_tokens = set(left.lower().split())
    right_tokens = set(right.lower().split())
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return overlap / float(union) if union else 0.0


def _input_id(input_value: object) -> str:
    payload = canonical_json_dumps(input_value, pretty=False, drop_run_keys=False)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest[:12]


def _summarize_metrics(results: list[dict]) -> dict:
    accuracy_values = []
    similarity_values = []
    for result in results:
        metrics = result.get("metrics") or {}
        if isinstance(metrics, dict):
            if metrics.get("accuracy") is not None:
                accuracy_values.append(float(metrics.get("accuracy") or 0.0))
            if metrics.get("similarity") is not None:
                similarity_values.append(float(metrics.get("similarity") or 0.0))
    summary: dict[str, object] = {}
    if accuracy_values:
        summary["accuracy"] = sum(accuracy_values) / len(accuracy_values)
    if similarity_values:
        summary["similarity"] = sum(similarity_values) / len(similarity_values)
    summary["cases"] = len(results)
    return summary


def _write_eval_payload(payload: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / PROMPT_EVAL_FILENAME
    canonical_json_dump(path, payload, pretty=True)


def _default_eval_dir(app_path: Path, prompt_name: str) -> Path:
    root = resolve_persistence_root(app_path.parent, app_path, allow_create=True)
    base = Path(root) / ".namel3ss" / "observability" / EVALS_DIRNAME / prompt_name
    return base


__all__ = ["run_prompt_eval", "load_prompt_evals", "PROMPT_EVAL_FILENAME"]
