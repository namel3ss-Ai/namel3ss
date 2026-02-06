from __future__ import annotations

import time
from pathlib import Path

from namel3ss.runtime.server.cluster_control import ClusterControlPlane


class _FakePool:
    def __init__(self) -> None:
        self.workers = 1
        self._depth = [4, 0, 0]
        self._index = 0
        self.resized: list[int] = []

    def queue_depth(self) -> int:
        if self._index >= len(self._depth):
            return self._depth[-1]
        value = self._depth[self._index]
        self._index += 1
        return value

    def resize(self, workers: int) -> None:
        value = max(1, int(workers))
        self.workers = value
        self.resized.append(value)


class _FakeServer:
    process_model = "worker_pool:1"


def test_cluster_control_plane_scales_worker_pool(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    (tmp_path / "cluster.yaml").write_text(
        (
            "cluster:\n"
            "  nodes:\n"
            "    - name: node1\n"
            "      host: 127.0.0.1\n"
            "      role: worker\n"
            "      capacity: 1core-1GB\n"
            "  scaling_policy:\n"
            "    target_cpu_percent: 10\n"
            "    min_nodes: 1\n"
            "    max_nodes: 3\n"
            "    scaling_interval: 1\n"
            "  rolling_update:\n"
            "    max_unavailable: 1\n"
        ),
        encoding="utf-8",
    )
    pool = _FakePool()
    server = _FakeServer()
    plane = ClusterControlPlane(project_root=tmp_path, app_path=app_path, worker_pool=pool, server=server)
    assert plane.start() is True
    try:
        time.sleep(1.3)
    finally:
        plane.stop()
    assert 2 in pool.resized
    assert str(server.process_model).startswith("worker_pool:")

