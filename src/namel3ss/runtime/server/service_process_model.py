from __future__ import annotations

from namel3ss.runtime.server.worker_pool import ServiceActionWorkerPool, capability_enabled


def configure_server_process_model(
    *,
    server,
    program_ir,
    app_path,
    concurrency,
    ui_mode: str,
    diagnostics_enabled: bool = False,
) -> ServiceActionWorkerPool | None:
    worker_processes = int(getattr(concurrency, "worker_processes", 1))
    performance_enabled = capability_enabled(program_ir, "performance") or capability_enabled(
        program_ir, "performance_scalability"
    )
    if performance_enabled and worker_processes > 1:
        worker_pool = ServiceActionWorkerPool(
            app_path=app_path,
            workers=worker_processes,
            ui_mode=ui_mode,
            diagnostics_enabled=diagnostics_enabled,
        )
        server.worker_pool = worker_pool  # type: ignore[attr-defined]
        server.process_model = f"worker_pool:{worker_processes}"  # type: ignore[attr-defined]
        return worker_pool
    server.worker_pool = None  # type: ignore[attr-defined]
    server.process_model = "service"  # type: ignore[attr-defined]
    return None


__all__ = ["configure_server_process_model"]
