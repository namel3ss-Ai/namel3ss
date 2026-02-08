from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, TimeoutError
import multiprocessing
from pathlib import Path
import threading

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.capabilities import normalize_builtin_capability
from namel3ss.module_loader import load_project
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.ui.actions.dispatch import dispatch_ui_action


class ServiceActionWorkerPool:
    def __init__(self, *, app_path: Path, workers: int, ui_mode: str, diagnostics_enabled: bool = False) -> None:
        self.app_path = Path(app_path).resolve()
        self.workers = max(1, int(workers))
        self.ui_mode = str(ui_mode)
        self.diagnostics_enabled = bool(diagnostics_enabled)
        self._lock = threading.RLock()
        self._pending = 0
        self._executor = _create_executor(self.workers)

    def run_action(self, action_id: str, payload: dict, *, timeout_seconds: float = 30.0) -> dict:
        future = self._submit(
            _run_action_worker,
            self.app_path.as_posix(),
            str(action_id),
            dict(payload or {}),
            self.ui_mode,
            self.diagnostics_enabled,
        )
        try:
            result = future.result(timeout=timeout_seconds)
        except TimeoutError as err:
            raise Namel3ssError(_worker_timeout_message(timeout_seconds)) from err
        except Exception as err:
            raise Namel3ssError(_worker_failed_message(str(err))) from err
        finally:
            self._mark_complete()
        if isinstance(result, dict):
            return result
        raise Namel3ssError(_worker_failed_message("Worker returned invalid payload."))

    def run_flow(
        self,
        *,
        program,
        flow_name: str,
        input: dict | None,
        identity: dict | None,
        route_name: str | None,
        timeout_seconds: float = 30.0,
        **_unused,
    ):
        future = self._submit(
            _run_flow_worker,
            self.app_path.as_posix(),
            str(flow_name),
            dict(input or {}),
            dict(identity or {}),
            str(route_name or ""),
        )
        try:
            result = future.result(timeout=timeout_seconds)
        except TimeoutError as err:
            raise Namel3ssError(_worker_timeout_message(timeout_seconds)) from err
        except Exception as err:
            raise Namel3ssError(_worker_failed_message(str(err))) from err
        finally:
            self._mark_complete()
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise Namel3ssError(_worker_failed_message("Flow worker returned invalid payload."))
        return _WorkerFlowResult(
            last_value=result.get("last_value"),
            yield_messages=result.get("yield_messages") if isinstance(result.get("yield_messages"), list) else [],
        )

    def queue_depth(self) -> int:
        with self._lock:
            return int(self._pending)

    def resize(self, workers: int) -> None:
        target = max(1, int(workers))
        with self._lock:
            if target == self.workers:
                return
            self._executor.shutdown(wait=True, cancel_futures=True)
            self.workers = target
            self._executor = _create_executor(self.workers)

    def shutdown(self) -> None:
        with self._lock:
            self._executor.shutdown(wait=True, cancel_futures=True)

    def _submit(self, fn, *args):
        with self._lock:
            self._pending += 1
            return self._executor.submit(fn, *args)

    def _mark_complete(self) -> None:
        with self._lock:
            self._pending = max(0, self._pending - 1)


def capability_enabled(program: object, capability: str) -> bool:
    values = getattr(program, "capabilities", ()) or ()
    if not isinstance(values, (list, tuple)):
        return False
    expected = normalize_builtin_capability(capability) or str(capability).strip().lower()
    for item in values:
        token = normalize_builtin_capability(item if isinstance(item, str) else None)
        if token == expected:
            return True
    return False


class _WorkerFlowResult:
    def __init__(self, *, last_value: object, yield_messages: list[dict]) -> None:
        self.last_value = last_value
        self.yield_messages = yield_messages


def _create_executor(workers: int) -> ProcessPoolExecutor:
    context = multiprocessing.get_context("spawn")
    return ProcessPoolExecutor(max_workers=max(1, int(workers)), mp_context=context)


def _run_action_worker(
    app_path: str,
    action_id: str,
    payload: dict,
    ui_mode: str,
    diagnostics_enabled: bool,
) -> dict:
    app_file = Path(app_path).resolve()
    source = app_file.read_text(encoding="utf-8")
    project = load_project(app_file, source_overrides={app_file: source})
    response = dispatch_ui_action(
        project.program,
        action_id=action_id,
        payload=payload,
        ui_mode=ui_mode,
        diagnostics_enabled=diagnostics_enabled,
    )
    if isinstance(response, dict):
        response.setdefault("process_model", "worker_pool")
        return response
    return {
        "ok": False,
        "error": {
            "message": "Action worker returned invalid response.",
            "kind": "engine",
        },
    }


def _run_flow_worker(app_path: str, flow_name: str, payload: dict, identity: dict, route_name: str) -> dict:
    app_file = Path(app_path).resolve()
    source = app_file.read_text(encoding="utf-8")
    project = load_project(app_file, source_overrides={app_file: source})
    result = execute_program_flow(
        project.program,
        flow_name,
        input=dict(payload or {}),
        identity=dict(identity or {}),
        auth_context=None,
        route_name=route_name or None,
    )
    return {
        "ok": True,
        "last_value": result.last_value,
        "yield_messages": list(getattr(result, "yield_messages", []) or []),
        "process_model": "worker_pool",
    }


def _worker_timeout_message(timeout_seconds: float) -> str:
    return build_guidance_message(
        what="Worker process timed out.",
        why=f"Action execution exceeded {timeout_seconds:.1f}s timeout.",
        fix="Reduce CPU-heavy work or increase worker timeout.",
        example="concurrency.yaml: worker_processes: 2",
    )


def _worker_failed_message(reason: str) -> str:
    return build_guidance_message(
        what="Worker process failed to execute action.",
        why=f"Worker error: {reason}",
        fix="Check worker logs and action payload for invalid data.",
        example='POST /api/action {"id":"page.home.button.send","payload":{}}',
    )


__all__ = ["ServiceActionWorkerPool", "capability_enabled"]
