from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.governance.verify import run_verify
from namel3ss.module_loader import load_project
from namel3ss.proofs.builder import build_engine_proof
from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.tools.runners.base import ToolRunnerResult
from namel3ss.secrets.redaction import _KNOWN_ENV_VARS
from namel3ss.ui.manifest import build_manifest


SPEC_ROOT = Path(__file__).resolve().parents[2] / "spec"
PROGRAMS_ROOT = SPEC_ROOT / "programs"
FAILURES_ROOT = SPEC_ROOT / "failures"
EXPECTED_ROOT = SPEC_ROOT / "expected"

_TIME_KEYS = {"timestamp", "time", "time_start", "time_end"}


def _clear_secret_env(env_ctx: pytest.MonkeyPatch) -> None:
    for key in _KNOWN_ENV_VARS:
        env_ctx.delenv(key, raising=False)


class StubRunner:
    def __init__(self, name: str, metadata: dict[str, object]) -> None:
        self.name = name
        self._metadata = dict(metadata)

    def execute(self, request):  # type: ignore[override]
        metadata = dict(self._metadata)
        metadata.setdefault("runner", self.name)
        return ToolRunnerResult(
            ok=True,
            output={"result": {"ok": True}},
            error_type=None,
            error_message=None,
            metadata=metadata,
        )


class _ServiceFixtureHandler(BaseHTTPRequestHandler):
    handshake_payload: dict = {"ok": True, "enforcement": "enforced", "supported_guarantees": {}}
    tool_payload: dict = {"ok": True, "result": {}}

    def log_message(self, format: str, *args) -> None:  # pragma: no cover - silence
        pass

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        _ = self.rfile.read(length) if length else b""
        if self.path == "/capabilities/handshake":
            payload = _ServiceFixtureHandler.handshake_payload
        elif self.path.endswith("/tools"):
            payload = _ServiceFixtureHandler.tool_payload
        else:
            self.send_error(404)
            return
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _start_service_fixture(handshake: dict, response: dict) -> tuple[HTTPServer, threading.Thread, str]:
    _ServiceFixtureHandler.handshake_payload = handshake
    _ServiceFixtureHandler.tool_payload = response
    server = HTTPServer(("127.0.0.1", 0), _ServiceFixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/tools"
    return server, thread, url


def _clear_service_handshake_cache() -> None:
    try:
        from namel3ss.runtime.tools.runners import service_runner

        service_runner._HANDSHAKE_CACHE.clear()
    except Exception:
        return


def _patch_tool_runners(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "namel3ss.runtime.tools.runners.registry._RUNNERS",
        {
            "local": StubRunner(
                "local",
                {
                    "python_env": "system",
                    "python_path": "<python_path>",
                    "deps_source": "none",
                    "protocol_version": 1,
                },
            ),
            "service": StubRunner(
                "service",
                {
                    "service_url": "http://service.local/tools",
                    "protocol_version": 1,
                },
            ),
            "container": StubRunner(
                "container",
                {
                    "container_runtime": "docker",
                    "image": "ghcr.io/namel3ss/tools:latest",
                    "command": "python -m namel3ss_tools.runner",
                    "protocol_version": 1,
                },
            ),
        },
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_spec_meta(path: Path) -> dict:
    meta_path = path.with_suffix(".spec.json")
    if not meta_path.exists():
        return {}
    return _read_json(meta_path)


def _expand_env(env: dict, app_root: Path, repo_root: Path) -> dict[str, str]:
    expanded: dict[str, str] = {}
    for key, value in env.items():
        rendered = str(value)
        rendered = rendered.replace("{app_root}", app_root.as_posix())
        rendered = rendered.replace("{repo_root}", repo_root.as_posix())
        expanded[str(key)] = rendered
    return expanded


def _reset_db(env: dict[str, str]) -> None:
    path = env.get("N3_DB_PATH")
    if not path:
        return
    for suffix in ("", "-wal", "-shm"):
        try:
            Path(f"{path}{suffix}").unlink()
        except FileNotFoundError:
            continue


def _normalize_path(value: str, repo_root: Path) -> str:
    if value.startswith("http://") or value.startswith("https://"):
        return value
    try:
        path = Path(value)
    except Exception:
        return value
    if not path.is_absolute():
        return value
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except Exception:
        return value


def _normalize_text(value: str, repo_root: Path) -> str:
    try:
        root = repo_root.resolve()
    except Exception:
        return value
    for candidate in {root.as_posix(), str(root)}:
        if candidate and candidate in value:
            value = value.replace(candidate, "<repo_root>")
    value = re.sub(r"http://127\.0\.0\.1:\d+", "http://127.0.0.1:<port>", value)
    return value


def _normalize_payload(value, repo_root: Path):
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            if key in _TIME_KEYS:
                normalized[key] = "<timestamp>"
            elif key == "duration_ms":
                normalized[key] = 0
            elif key == "proof_id":
                normalized[key] = "<proof_id>"
            elif key == "python_path":
                normalized[key] = "<python_path>"
            else:
                normalized[key] = _normalize_payload(item, repo_root)
        return normalized
    if isinstance(value, list):
        return [_normalize_payload(item, repo_root) for item in value]
    if isinstance(value, str):
        normalized = _normalize_path(value, repo_root)
        return _normalize_text(normalized, repo_root)
    return value


def _trace_to_dict(trace) -> dict:
    if hasattr(trace, "__dict__"):
        return trace.__dict__
    return trace if isinstance(trace, dict) else {"value": trace}


def _select_flow(program, requested: str | None) -> str:
    if requested:
        return requested
    flows = [flow.name for flow in program.flows]
    if len(flows) == 1:
        return flows[0]
    raise AssertionError("Spec program must declare exactly one flow or set 'flow' in .spec.json")


def _run_flow(program, *, flow_name: str, input_data: dict | None) -> dict:
    result = execute_program_flow(program, flow_name, state=None, input=input_data or {})
    traces = [_trace_to_dict(t) for t in result.traces]
    return {"ok": True, "state": result.state, "result": result.last_value, "traces": traces}


def _run_spec(path: Path, meta: dict) -> dict:
    mode = meta.get("mode", "flow")
    repo_root = Path(__file__).resolve().parents[2]
    app_root = path.parent
    if mode == "ui":
        project = load_project(path)
        manifest = build_manifest(project.program, store=MemoryStore())
        return _normalize_payload(manifest, repo_root)
    if mode == "proof":
        target = meta.get("target", "local")
        _, proof = build_engine_proof(path, target=target)
        return _normalize_payload(proof, repo_root)
    if mode == "verify":
        target = meta.get("target", "local")
        prod = bool(meta.get("prod", False))
        payload = run_verify(path, target=target, prod=prod)
        return _normalize_payload(payload, repo_root)

    project = load_project(path)
    program = project.program
    flow_name = _select_flow(program, meta.get("flow"))
    runs = meta.get("runs")
    if runs:
        if not isinstance(runs, list):
            raise AssertionError("Spec 'runs' must be a list")
        outputs = []
        for run in runs:
            run_flow = flow_name
            run_input = meta.get("input")
            if isinstance(run, dict):
                run_flow = run.get("flow", run_flow)
                run_input = run.get("input", run_input)
            outputs.append(_normalize_payload(_run_flow(program, flow_name=run_flow, input_data=run_input), repo_root))
        return {"runs": outputs}
    output = _run_flow(program, flow_name=flow_name, input_data=meta.get("input"))
    return _normalize_payload(output, repo_root)


def _expected_output_path(path: Path) -> Path:
    relative = path.relative_to(PROGRAMS_ROOT)
    return EXPECTED_ROOT / relative.with_suffix(".json")


def _expected_failure_path(path: Path) -> Path:
    return path.with_suffix(".json")


@pytest.mark.parametrize("spec_path", sorted(PROGRAMS_ROOT.rglob("*.ai")))
def test_executable_spec_programs(monkeypatch: pytest.MonkeyPatch, spec_path: Path) -> None:
    expected_path = _expected_output_path(spec_path)
    assert expected_path.exists(), f"Missing expected output: {expected_path}"
    meta = _load_spec_meta(spec_path)
    if not meta.get("use_real_runners"):
        _patch_tool_runners(monkeypatch)
    env = meta.get("env", {})
    if env and not isinstance(env, dict):
        raise AssertionError("Spec 'env' must be a mapping")

    repo_root = Path(__file__).resolve().parents[2]
    app_root = spec_path.parent
    expanded_env = _expand_env(env, app_root, repo_root) if env else {}
    if expanded_env:
        _reset_db(expanded_env)
    with monkeypatch.context() as env_ctx:
        _clear_secret_env(env_ctx)
        for key, value in expanded_env.items():
            env_ctx.setenv(key, value)
        server = None
        thread = None
        try:
            fixture = meta.get("service_fixture")
            if fixture:
                if not isinstance(fixture, dict):
                    raise AssertionError("Spec 'service_fixture' must be a mapping")
                handshake = fixture.get("handshake") or {"ok": True, "enforcement": "enforced", "supported_guarantees": {}}
                response = fixture.get("response") or {"ok": True, "result": {}}
                if not isinstance(handshake, dict) or not isinstance(response, dict):
                    raise AssertionError("Spec 'service_fixture' must include handshake/response objects")
                server, thread, url = _start_service_fixture(handshake, response)
                env_ctx.setenv("N3_TOOL_SERVICE_URL", url)
                _clear_service_handshake_cache()
            output = _run_spec(spec_path, meta)
        finally:
            if server is not None:
                server.shutdown()
            if thread is not None:
                thread.join(timeout=1)
    expected = _read_json(expected_path)
    assert output == expected


@pytest.mark.parametrize("spec_path", sorted(FAILURES_ROOT.rglob("*.ai")))
def test_executable_spec_failures(monkeypatch: pytest.MonkeyPatch, spec_path: Path) -> None:
    expected_path = _expected_failure_path(spec_path)
    assert expected_path.exists(), f"Missing failure expectation: {expected_path}"
    meta = _load_spec_meta(spec_path)
    if not meta.get("use_real_runners"):
        _patch_tool_runners(monkeypatch)
    env = meta.get("env", {})
    if env and not isinstance(env, dict):
        raise AssertionError("Spec 'env' must be a mapping")

    repo_root = Path(__file__).resolve().parents[2]
    app_root = spec_path.parent
    expanded_env = _expand_env(env, app_root, repo_root) if env else {}
    if expanded_env:
        _reset_db(expanded_env)
    err = None
    with monkeypatch.context() as env_ctx:
        _clear_secret_env(env_ctx)
        for key, value in expanded_env.items():
            env_ctx.setenv(key, value)
        try:
            server = None
            thread = None
            fixture = meta.get("service_fixture")
            if fixture:
                if not isinstance(fixture, dict):
                    raise AssertionError("Spec 'service_fixture' must be a mapping")
                handshake = fixture.get("handshake") or {"ok": True, "enforcement": "enforced", "supported_guarantees": {}}
                response = fixture.get("response") or {"ok": True, "result": {}}
                if not isinstance(handshake, dict) or not isinstance(response, dict):
                    raise AssertionError("Spec 'service_fixture' must include handshake/response objects")
                server, thread, url = _start_service_fixture(handshake, response)
                env_ctx.setenv("N3_TOOL_SERVICE_URL", url)
                _clear_service_handshake_cache()
            _run_spec(spec_path, meta)
        except Exception as exc:  # noqa: BLE001
            err = exc
        finally:
            if server is not None:
                server.shutdown()
            if thread is not None:
                thread.join(timeout=1)
    assert err is not None, "Expected spec failure, but run succeeded"
    message = str(err)
    expected = _read_json(expected_path)
    for key, prefix in {
        "what": "What happened: ",
        "why": "Why: ",
        "fix": "Fix: ",
        "example": "Example: ",
    }.items():
        if key in expected:
            assert f"{prefix}{expected[key]}" in message
    extra = expected.get("contains", [])
    if extra:
        for fragment in extra:
            assert fragment in message
    if isinstance(err, Namel3ssError):
        return
    raise AssertionError(f"Unexpected error type: {type(err).__name__}")
