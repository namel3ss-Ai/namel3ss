from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, TimeoutError
import multiprocessing
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.capabilities import normalize_builtin_capability
from namel3ss.module_loader import load_project
from namel3ss.ui.actions.dispatch import dispatch_ui_action


class ServiceActionWorkerPool:
    def __init__(self, *, app_path: Path, workers: int) -> None:
        self.app_path = Path(app_path).resolve()
        self.workers = max(1, int(workers))
        context = multiprocessing.get_context("spawn")
        self._executor = ProcessPoolExecutor(max_workers=self.workers, mp_context=context)

    def run_action(self, action_id: str, payload: dict, *, timeout_seconds: float = 30.0) -> dict:
        future = self._executor.submit(
            _run_action_worker,
            self.app_path.as_posix(),
            str(action_id),
            dict(payload or {}),
        )
        try:
            result = future.result(timeout=timeout_seconds)
        except TimeoutError as err:
            raise Namel3ssError(_worker_timeout_message(timeout_seconds)) from err
        except Exception as err:
            raise Namel3ssError(_worker_failed_message(str(err))) from err
        if isinstance(result, dict):
            return result
        raise Namel3ssError(_worker_failed_message("Worker returned invalid payload."))

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)


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


def _run_action_worker(app_path: str, action_id: str, payload: dict) -> dict:
    app_file = Path(app_path).resolve()
    source = app_file.read_text(encoding="utf-8")
    project = load_project(app_file, source_overrides={app_file: source})
    response = dispatch_ui_action(project.program, action_id=action_id, payload=payload)
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
