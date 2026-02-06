from __future__ import annotations

import threading
from pathlib import Path

from namel3ss.cluster import load_cluster_config, scale_cluster
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.server.worker_pool import ServiceActionWorkerPool


class ClusterControlPlane:
    def __init__(
        self,
        *,
        project_root: Path,
        app_path: Path,
        worker_pool: ServiceActionWorkerPool | None,
        server,
    ) -> None:
        self.project_root = Path(project_root)
        self.app_path = Path(app_path)
        self.worker_pool = worker_pool
        self.server = server
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> bool:
        if self.worker_pool is None:
            return False
        try:
            config = load_cluster_config(self.project_root, self.app_path, required=False)
        except Exception:
            return False
        if not config.nodes and config.scaling_policy.max_nodes <= 1:
            return False
        interval = max(1, int(config.scaling_policy.scaling_interval))
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            kwargs={"interval_seconds": interval},
            daemon=True,
            name="n3-cluster-control",
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def _run_loop(self, *, interval_seconds: int) -> None:
        while not self._stop.wait(float(interval_seconds)):
            pool = self.worker_pool
            if pool is None:
                continue
            pending = pool.queue_depth()
            workers = max(1, int(pool.workers))
            cpu_percent = min(100.0, (float(pending) * 100.0) / float(workers))
            try:
                result = scale_cluster(
                    project_root=self.project_root,
                    app_path=self.app_path,
                    cpu_percent=cpu_percent,
                )
            except Namel3ssError:
                continue
            except Exception:
                continue
            desired = int(result.get("to_nodes") or workers)
            if desired != workers:
                pool.resize(desired)
                self.server.process_model = f"worker_pool:{desired}"  # type: ignore[attr-defined]


__all__ = ["ClusterControlPlane"]

