from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.nodes import lower_program
from namel3ss.module_loader import load_project
from namel3ss.parser.core import parse
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.traces.schema import TraceEventType


DX_SCHEMA_VERSION = 1
_SECRET_ENV_KEYS = {
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "MISTRAL_API_KEY",
    "OPENAI_API_KEY",
    "NAMEL3SS_OPENAI_API_KEY",
    "NAMEL3SS_ANTHROPIC_API_KEY",
    "NAMEL3SS_GEMINI_API_KEY",
    "NAMEL3SS_MISTRAL_API_KEY",
    "N3_DATABASE_URL",
    "N3_EDGE_KV_URL",
}


@dataclass
class _RunRecord:
    result: object | None
    store: MemoryStore | None
    program: object | None
    error: str | None = None


def run_verify_dx(
    *,
    app_path: Path | None = None,
    project_root: Path | None = None,
) -> dict:
    root = project_root or (app_path.parent if app_path else Path.cwd())
    templates_root = root / "src" / "namel3ss" / "templates"
    studio_root = root / "src" / "namel3ss" / "studio" / "web"
    checks: dict[str, dict] = {}
    if not templates_root.exists() or not studio_root.exists():
        missing = []
        if not templates_root.exists():
            missing.append("templates")
        if not studio_root.exists():
            missing.append("studio")
        checks["repo_layout"] = _check(
            "fail",
            "DX verify requires a namel3ss repo checkout.",
            {"missing": missing},
        )
        return {"ok": False, "status": "fail", "schema_version": DX_SCHEMA_VERSION, "dx": checks}
    runs = _run_flagship_templates(templates_root)
    checks["template_zero_setup"] = _check_template_zero_setup(runs)
    checks["silent_failure"] = _check_silent_failure(runs)
    checks["secret_leaks"] = _check_secret_leaks(runs)
    checks["type_contract"] = _check_type_contract(runs)
    checks["studio_invariants"] = _check_studio_invariants(studio_root)

    ok = all(check.get("status") == "ok" for check in checks.values())
    return {"ok": ok, "status": "ok" if ok else "fail", "schema_version": DX_SCHEMA_VERSION, "dx": checks}


def _run_flagship_templates(templates_root: Path) -> dict[str, _RunRecord]:
    runs: dict[str, _RunRecord] = {}
    demo_path = templates_root / "demo" / "app.ai"
    starter_path = templates_root / "starter" / "app.ai"

    runs["demo"] = _run_demo(demo_path)
    runs["starter"] = _run_starter(starter_path)
    runs["openai_failure"] = _run_openai_probe(_openai_failure("sk-test-secret"))
    runs["coercion"] = _run_type_coercion()
    runs["coercion_strict"] = _run_type_coercion(strict=True)
    return runs


def _run_demo(app_path: Path) -> _RunRecord:
    if not app_path.exists():
        return _RunRecord(None, None, None, error=f"Missing template: {app_path}")
    config = AppConfig()
    try:
        with _isolated_secret_env({}), _suppress_dotenv():
            project = load_project(app_path)
            store = MemoryStore()
            result = execute_program_flow(
                project.program,
                "ask_ai",
                store=store,
                input={"message": "hello"},
                config=config,
            )
            return _RunRecord(result=result, store=store, program=project.program)
    except Exception as err:
        return _RunRecord(None, None, None, error=str(err))


def _run_starter(app_path: Path) -> _RunRecord:
    if not app_path.exists():
        return _RunRecord(None, None, None, error=f"Missing template: {app_path}")
    config = AppConfig()
    try:
        with _isolated_secret_env({}), _suppress_dotenv():
            project = load_project(app_path)
            store = MemoryStore()
            result = execute_program_flow(project.program, "seed_note", store=store, config=config)
            return _RunRecord(result=result, store=store, program=project.program)
    except Exception as err:
        return _RunRecord(None, None, None, error=str(err))


def _run_type_coercion(*, strict: bool = False) -> _RunRecord:
    source = '''spec is "1.0"

record "Note":
  field "text" is text

flow "demo": requires true
  set state.note.text is map:
    "output" is "hello"
  create "Note" with state.note as note
  return state.note.text
'''
    config = AppConfig()
    strict_value = "1" if strict else ""
    try:
        with _isolated_secret_env({}), _suppress_dotenv(), _temporary_env(
            {"NAMEL3SS_STRICT_TEXT_FIELDS": strict_value}
        ):
            program = lower_program(parse(source))
            store = MemoryStore()
            result = execute_program_flow(program, "demo", store=store, config=config)
            return _RunRecord(result=result, store=store, program=program)
    except Exception as err:
        return _RunRecord(None, None, None, error=str(err))


def _run_openai_probe(outcome: dict | Exception) -> _RunRecord:
    source = '''spec is "1.0"

ai "assistant_openai":
  provider is "openai"
  model is "gpt-4.1"
  system_prompt is "DX probe"

flow "probe": requires true
  attempt:
    ask ai "assistant_openai" with input: "hello" as reply
    set state.status with:
      message is "AI Mode: OpenAI"
  otherwise:
    set state.status with:
      message is "Using mock fallback"
    return "fallback"
  return reply
'''
    config = AppConfig()
    try:
        with _isolated_secret_env({"NAMEL3SS_OPENAI_API_KEY": "sk-test-secret"}), _suppress_dotenv():
            with _patch_openai_post_json(outcome):
                program = lower_program(parse(source))
                store = MemoryStore()
                result = execute_program_flow(program, "probe", store=store, config=config)
                return _RunRecord(result=result, store=store, program=program)
    except Exception as err:
        return _RunRecord(None, None, None, error=str(err))


def _check_template_zero_setup(runs: dict[str, _RunRecord]) -> dict:
    failures: list[str] = []
    demo = runs.get("demo")
    starter = runs.get("starter")

    _assert_run_ok(demo, "demo", failures)
    _assert_run_ok(starter, "starter", failures)

    if failures:
        return _check("fail", "Template zero-setup checks failed.", {"failures": failures})
    return _check("ok", "Templates run with zero setup using defaults.")


def _check_silent_failure(runs: dict[str, _RunRecord]) -> dict:
    failures: list[str] = []
    failure_run = runs.get("openai_failure")
    _assert_run_ok(failure_run, "openai failure", failures)
    diagnostic = None
    if failure_run and failure_run.result:
        events = _collect_trace_events(failure_run.result.traces)
        diag_events = [event for event in events if event.get("type") == TraceEventType.AI_PROVIDER_ERROR]
        if not diag_events:
            failures.append("ai_provider_error trace missing on OpenAI failure")
        else:
            diagnostic = diag_events[0].get("diagnostic") if isinstance(diag_events[0], dict) else None
        status = _status_message(failure_run.result)
        if "fallback" not in status.lower():
            failures.append("Fallback status message missing for OpenAI failure")
    if diagnostic:
        required_fields = ["provider", "url", "status", "code", "type", "message", "category", "hint", "severity"]
        for field in required_fields:
            if not diagnostic.get(field):
                failures.append(f"diagnostic missing {field}")
    if failures:
        return _check("fail", "Provider failures lacked diagnostics or explicit fallback.", {"failures": failures})
    return _check("ok", "Provider failures emit diagnostics and explicit fallback status.")


def _check_secret_leaks(runs: dict[str, _RunRecord]) -> dict:
    failures: list[str] = []
    failure_run = runs.get("openai_failure")
    if failure_run and failure_run.result:
        secret_values = ["sk-test-secret"]
        leak_sources = [
            ("traces", failure_run.result.traces),
            ("state", getattr(failure_run.result, "state", {})),
            ("result", getattr(failure_run.result, "last_value", None)),
        ]
        for label, payload in leak_sources:
            leaks = _find_leaks(_serialize(payload), secret_values)
            if leaks:
                failures.append(f"{label} leaked {', '.join(leaks)}")
        events = _collect_trace_events(failure_run.result.traces)
        diag_events = [event for event in events if event.get("type") == TraceEventType.AI_PROVIDER_ERROR]
        if diag_events:
            diagnostic = diag_events[0].get("diagnostic") if isinstance(diag_events[0], dict) else {}
            if _contains_sensitive_keys(diagnostic):
                failures.append("diagnostic contained headers or auth material")
    else:
        failures.append("missing OpenAI failure run for secret leak scan")

    if failures:
        return _check("fail", "Secret leakage detected in DX outputs.", {"failures": failures})
    return _check("ok", "No secret values or auth headers detected in DX outputs.")


def _check_type_contract(runs: dict[str, _RunRecord]) -> dict:
    failures: list[str] = []
    demo = runs.get("demo")
    coercion = runs.get("coercion")
    strict = runs.get("coercion_strict")

    if demo and demo.result:
        if not isinstance(demo.result.last_value, str):
            failures.append("demo ask_ai did not return text")
        answers = _record_rows(demo, "Answer")
        if not answers:
            failures.append("demo did not create Answer records")
        else:
            reply = answers[-1].get("reply")
            why = answers[-1].get("why")
            if not isinstance(reply, str) or not reply.strip():
                failures.append("Answer.reply missing or not text in demo")
            if not isinstance(why, str) or not why.strip():
                failures.append("Answer.why missing or not text in demo")
    else:
        failures.append("missing demo run for ai contract")

    if coercion and coercion.result and coercion.store and coercion.program:
        note_text = _record_field_value(coercion, "Note", "text")
        if not isinstance(note_text, str):
            failures.append("Text coercion did not store string for Note.text")
    else:
        failures.append("Missing coercion run for record text enforcement")

    if strict and strict.error is None:
        failures.append("Strict text mode did not fail on non-text value")

    if failures:
        return _check("fail", "Type contract checks failed.", {"failures": failures})
    return _check("ok", "AI and record text fields enforce text contract.")


def _check_studio_invariants(studio_root: Path) -> dict:
    failures: list[str] = []
    html_path = studio_root / "index.html"
    setup_path = studio_root / "studio" / "setup.js"
    if not html_path.exists() or not setup_path.exists():
        failures.append("Studio UI files are missing.")
        return _check("fail", "Studio invariants missing.", {"failures": failures})
    html = html_path.read_text(encoding="utf-8")
    setup_js = setup_path.read_text(encoding="utf-8")
    for needle in ['id="aiModeBadge"', 'id="aiModeBadgeSetup"', "Open Setup"]:
        if needle not in html:
            failures.append(f"Missing Studio badge markup: {needle}")
    for needle in ["updateAiBadge", "aiModeBadgeSetup", "sanitizeSecretName", "Missing secrets:"]:
        if needle not in setup_js:
            failures.append(f"Missing Studio setup logic: {needle}")
    if "secret.value" in setup_js:
        failures.append("Setup panel should not reference secret values.")
    if failures:
        return _check("fail", "Studio invariants are missing.", {"failures": failures})
    return _check("ok", "Studio shows AI mode badge and missing secrets guidance.")


def _check(status: str, message: str, details: dict | None = None) -> dict:
    payload = {"status": status, "message": message}
    if details:
        payload["details"] = details
    return payload


def _assert_run_ok(run: _RunRecord | None, label: str, failures: list[str]) -> None:
    if run is None or run.error or run.result is None:
        failures.append(f"{label} failed to execute")


def _status_message(result: object) -> str:
    state = getattr(result, "state", {}) if result else {}
    status = state.get("status", {}) if isinstance(state, dict) else {}
    message = status.get("message") if isinstance(status, dict) else ""
    return str(message or "")


def _record_field_value(run: _RunRecord, record_name: str, field: str) -> object | None:
    rows = _record_rows(run, record_name)
    if not rows:
        return None
    return rows[-1].get(field)


def _record_rows(run: _RunRecord, record_name: str) -> list[dict]:
    if not run.store or not run.program:
        return []
    schemas = {schema.name: schema for schema in getattr(run.program, "records", [])}
    schema = schemas.get(record_name)
    if not schema:
        return []
    return run.store.list_records(schema, limit=50)


def _collect_trace_events(traces: Iterable[object]) -> list[dict]:
    events: list[dict] = []
    for trace in traces or []:
        if isinstance(trace, dict):
            events.append(trace)
            continue
        canonical = getattr(trace, "canonical_events", None)
        if isinstance(canonical, list):
            events.extend([event for event in canonical if isinstance(event, dict)])
            continue
        if hasattr(trace, "__dict__") and isinstance(trace.__dict__, dict):
            events.append(trace.__dict__)
    return events


def _find_leaks(text: str, secret_values: list[str]) -> list[str]:
    leaks: list[str] = []
    if not text:
        return leaks
    if "Bearer " in text:
        leaks.append("Bearer")
    if re.search(r"sk-[A-Za-z0-9]{6,}", text):
        leaks.append("sk-")
    for secret in secret_values:
        if secret and secret in text:
            leaks.append("secret_value")
            break
    return sorted(set(leaks))


def _contains_sensitive_keys(payload: object) -> bool:
    sensitive = {"authorization", "headers", "auth", "api_key"}
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key).lower() in sensitive:
                return True
            if _contains_sensitive_keys(value):
                return True
    if isinstance(payload, list):
        return any(_contains_sensitive_keys(item) for item in payload)
    if isinstance(payload, str):
        return "Bearer " in payload
    return False


def _serialize(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except TypeError:
        return json.dumps(str(value), sort_keys=True)


def _openai_failure(secret: str) -> Exception:
    details = {
        "status": 401,
        "error": {
            "code": "invalid_api_key",
            "type": "invalid_request_error",
            "message": f"Invalid API key: {secret}",
        },
    }
    return Namel3ssError("Provider 'openai' authentication failed", details=details)


@contextmanager
def _patch_openai_post_json(
    outcome: dict | Exception,
):
    from namel3ss.runtime.ai.providers import openai as openai_provider

    original = openai_provider.post_json

    def _stub(**kwargs):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    openai_provider.post_json = _stub
    try:
        yield
    finally:
        openai_provider.post_json = original


@contextmanager
def _isolated_secret_env(overrides: dict[str, str]):
    saved = {key: os.environ.get(key) for key in _SECRET_ENV_KEYS}
    for key in _SECRET_ENV_KEYS:
        os.environ.pop(key, None)
    for key, value in overrides.items():
        os.environ[key] = value
    try:
        yield
    finally:
        for key in _SECRET_ENV_KEYS:
            original = saved.get(key)
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original


@contextmanager
def _temporary_env(overrides: dict[str, str]):
    if not overrides:
        yield
        return
    saved = {key: os.environ.get(key) for key in overrides}
    for key, value in overrides.items():
        os.environ[key] = value
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@contextmanager
def _suppress_dotenv():
    from namel3ss.config import loader as config_loader
    from namel3ss.secrets import discovery as secrets_discovery

    loader_original = config_loader.load_dotenv_for_path
    discovery_original = secrets_discovery.load_dotenv_for_path
    config_loader.load_dotenv_for_path = lambda _: {}
    secrets_discovery.load_dotenv_for_path = lambda _: {}
    try:
        yield
    finally:
        config_loader.load_dotenv_for_path = loader_original
        secrets_discovery.load_dotenv_for_path = discovery_original


__all__ = ["DX_SCHEMA_VERSION", "run_verify_dx"]
