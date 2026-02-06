from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_persistence_root, resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


CLUSTER_FILENAME = "cluster.yaml"
CLUSTER_STATE_FILENAME = "cluster_state.json"


@dataclass(frozen=True)
class ClusterNode:
    name: str
    host: str
    role: str
    capacity: str
    status: str = "unknown"

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "host": self.host,
            "role": self.role,
            "capacity": self.capacity,
            "status": self.status,
        }


@dataclass(frozen=True)
class ClusterPolicy:
    target_cpu_percent: int
    max_nodes: int
    min_nodes: int
    scaling_interval: int = 60

    def to_dict(self) -> dict[str, object]:
        return {
            "target_cpu_percent": int(self.target_cpu_percent),
            "max_nodes": int(self.max_nodes),
            "min_nodes": int(self.min_nodes),
            "scaling_interval": int(self.scaling_interval),
        }


@dataclass(frozen=True)
class ClusterRollingUpdate:
    max_unavailable: int = 1

    def to_dict(self) -> dict[str, object]:
        return {"max_unavailable": int(self.max_unavailable)}


@dataclass(frozen=True)
class ClusterConfig:
    nodes: tuple[ClusterNode, ...]
    scaling_policy: ClusterPolicy
    rolling_update: ClusterRollingUpdate

    def to_dict(self) -> dict[str, object]:
        return {
            "cluster": {
                "nodes": [item.to_dict() for item in self.sorted_nodes()],
                "scaling_policy": self.scaling_policy.to_dict(),
                "rolling_update": self.rolling_update.to_dict(),
            }
        }

    def sorted_nodes(self) -> tuple[ClusterNode, ...]:
        return tuple(sorted(self.nodes, key=lambda item: item.name))

    def worker_names(self) -> list[str]:
        workers = [node.name for node in self.nodes if node.role == "worker"]
        return sorted(workers)


@dataclass(frozen=True)
class ClusterState:
    active_nodes: int
    deployed_version: str | None
    events: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "active_nodes": int(self.active_nodes),
            "deployed_version": self.deployed_version or "",
            "events": [dict(item) for item in self.events],
        }


def cluster_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return Path(root) / CLUSTER_FILENAME


def cluster_state_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_persistence_root(project_root, app_path)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / CLUSTER_STATE_FILENAME


def load_cluster_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    required: bool = False,
) -> ClusterConfig:
    path = cluster_path(project_root, app_path)
    if path is None:
        if required:
            raise Namel3ssError(_missing_config_message("cluster.yaml"))
        return _default_config()
    if not path.exists():
        if required:
            raise Namel3ssError(_missing_config_message(path.as_posix()))
        return _default_config()
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_config_message(path, str(err))) from err
    return _parse_cluster_config(payload, path=path)


def save_cluster_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    config: ClusterConfig,
) -> Path:
    path = cluster_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Cluster config path could not be resolved.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(config.to_dict()), encoding="utf-8")
    return path


def load_cluster_state(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    config: ClusterConfig | None = None,
) -> ClusterState:
    cfg = config or load_cluster_config(project_root, app_path)
    path = cluster_state_path(project_root, app_path)
    if path is None or not path.exists():
        return _default_state(cfg)
    try:
        payload = json.loads(path.read_text(encoding="utf-8") or "{}")
    except Exception as err:
        raise Namel3ssError(_invalid_state_message(path)) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_state_message(path))
    raw_active = payload.get("active_nodes")
    active = _normalize_int(raw_active, field_name="active_nodes", minimum=0)
    active = _clamp(active, cfg.scaling_policy.min_nodes, cfg.scaling_policy.max_nodes)
    deployed_version = str(payload.get("deployed_version") or "").strip() or None
    raw_events = payload.get("events")
    events: list[dict[str, object]] = []
    if isinstance(raw_events, list):
        for row in raw_events:
            if isinstance(row, dict):
                events.append(dict(row))
    events.sort(key=lambda row: int(row.get("step_count") or 0))
    return ClusterState(active_nodes=active, deployed_version=deployed_version, events=tuple(events))


def cluster_status(project_root: str | Path | None, app_path: str | Path | None) -> dict[str, object]:
    config = load_cluster_config(project_root, app_path, required=True)
    state = load_cluster_state(project_root, app_path, config=config)
    return {
        "ok": True,
        "nodes": [item.to_dict() for item in config.sorted_nodes()],
        "worker_count": len(config.worker_names()),
        "active_nodes": state.active_nodes,
        "deployed_version": state.deployed_version or "",
        "scaling_policy": config.scaling_policy.to_dict(),
        "rolling_update": config.rolling_update.to_dict(),
        "event_count": len(state.events),
    }


def scale_cluster(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    cpu_percent: float,
) -> dict[str, object]:
    config = load_cluster_config(project_root, app_path, required=True)
    state = load_cluster_state(project_root, app_path, config=config)
    current = int(state.active_nodes)
    target = int(config.scaling_policy.target_cpu_percent)
    minimum = int(config.scaling_policy.min_nodes)
    maximum = int(config.scaling_policy.max_nodes)
    requested_cpu = float(cpu_percent)
    desired = current
    action = "hold"
    reason = "within_target"
    if requested_cpu > target and current < maximum:
        desired = current + 1
        action = "scale_up"
        reason = "cpu_above_target"
    elif requested_cpu < (target * 0.5) and current > minimum:
        desired = current - 1
        action = "scale_down"
        reason = "cpu_below_floor"
    event = {
        "step_count": _next_step(state.events),
        "action": action,
        "reason": reason,
        "cpu_percent": requested_cpu,
        "from_nodes": current,
        "to_nodes": desired,
        "node_name": _scaling_node_name(config, action, current, desired),
    }
    next_events = list(state.events)
    next_events.append(event)
    _write_cluster_state(
        project_root,
        app_path,
        ClusterState(active_nodes=desired, deployed_version=state.deployed_version, events=tuple(next_events)),
    )
    return {
        "ok": True,
        "action": action,
        "reason": reason,
        "cpu_percent": requested_cpu,
        "from_nodes": current,
        "to_nodes": desired,
        "event": event,
    }


def deploy_cluster(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    version: str,
) -> dict[str, object]:
    config = load_cluster_config(project_root, app_path, required=True)
    state = load_cluster_state(project_root, app_path, config=config)
    version_text = str(version or "").strip()
    if not version_text:
        raise Namel3ssError(_invalid_version_message())
    workers = _active_worker_names(config, state.active_nodes)
    max_unavailable = max(1, int(config.rolling_update.max_unavailable))
    step = _next_step(state.events)
    rollout: list[dict[str, object]] = []
    for start in range(0, len(workers), max_unavailable):
        batch = workers[start : start + max_unavailable]
        for node_name in batch:
            rollout.append({"step_count": step, "action": "start_new", "node_name": node_name, "version": version_text})
            step += 1
        for node_name in batch:
            rollout.append({"step_count": step, "action": "drain_old", "node_name": node_name, "version": version_text})
            step += 1
    rollout.append({"step_count": step, "action": "switch_traffic", "node_name": "all", "version": version_text})
    next_events = list(state.events) + rollout
    _write_cluster_state(
        project_root,
        app_path,
        ClusterState(active_nodes=state.active_nodes, deployed_version=version_text, events=tuple(next_events)),
    )
    return {
        "ok": True,
        "deployed_version": version_text,
        "active_nodes": state.active_nodes,
        "max_unavailable": max_unavailable,
        "rollout_steps": rollout,
    }


def _parse_cluster_config(payload: object, *, path: Path) -> ClusterConfig:
    if isinstance(payload, dict):
        root = payload.get("cluster", payload)
    else:
        root = {}
    if not isinstance(root, dict):
        raise Namel3ssError(_invalid_config_message(path, "cluster must be an object"))
    raw_nodes = root.get("nodes") or []
    if not isinstance(raw_nodes, list):
        raise Namel3ssError(_invalid_config_message(path, "cluster.nodes must be a list"))
    nodes: list[ClusterNode] = []
    seen_names: set[str] = set()
    for row in raw_nodes:
        if not isinstance(row, dict):
            raise Namel3ssError(_invalid_config_message(path, "cluster.nodes entries must be objects"))
        node = ClusterNode(
            name=_require_text(row.get("name"), "node.name"),
            host=_require_text(row.get("host"), "node.host"),
            role=_normalize_role(row.get("role")),
            capacity=_require_text(row.get("capacity"), "node.capacity"),
            status=str(row.get("status") or "unknown").strip() or "unknown",
        )
        if node.name in seen_names:
            raise Namel3ssError(_invalid_config_message(path, f"node '{node.name}' is duplicated"))
        seen_names.add(node.name)
        nodes.append(node)
    policy_raw = root.get("scaling_policy") if isinstance(root.get("scaling_policy"), dict) else {}
    rolling_raw = root.get("rolling_update") if isinstance(root.get("rolling_update"), dict) else {}
    policy = ClusterPolicy(
        target_cpu_percent=_normalize_int(policy_raw.get("target_cpu_percent", 70), field_name="target_cpu_percent", minimum=1),
        max_nodes=_normalize_int(policy_raw.get("max_nodes", max(1, len(nodes))), field_name="max_nodes", minimum=1),
        min_nodes=_normalize_int(policy_raw.get("min_nodes", 1), field_name="min_nodes", minimum=1),
        scaling_interval=_normalize_int(policy_raw.get("scaling_interval", 60), field_name="scaling_interval", minimum=1),
    )
    if policy.min_nodes > policy.max_nodes:
        raise Namel3ssError(_invalid_config_message(path, "scaling_policy.min_nodes cannot exceed max_nodes"))
    rolling = ClusterRollingUpdate(
        max_unavailable=_normalize_int(rolling_raw.get("max_unavailable", 1), field_name="max_unavailable", minimum=1)
    )
    return ClusterConfig(nodes=tuple(nodes), scaling_policy=policy, rolling_update=rolling)


def _default_config() -> ClusterConfig:
    policy = ClusterPolicy(target_cpu_percent=70, max_nodes=3, min_nodes=1, scaling_interval=60)
    rolling = ClusterRollingUpdate(max_unavailable=1)
    return ClusterConfig(nodes=(), scaling_policy=policy, rolling_update=rolling)


def _default_state(config: ClusterConfig) -> ClusterState:
    workers = len(config.worker_names())
    active = max(config.scaling_policy.min_nodes, workers if workers else config.scaling_policy.min_nodes)
    active = _clamp(active, config.scaling_policy.min_nodes, config.scaling_policy.max_nodes)
    return ClusterState(active_nodes=active, deployed_version=None, events=())


def _write_cluster_state(
    project_root: str | Path | None,
    app_path: str | Path | None,
    state: ClusterState,
) -> Path:
    path = cluster_state_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Cluster state path could not be resolved.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json_dumps(state.to_dict(), pretty=True, drop_run_keys=False), encoding="utf-8")
    return path


def _active_worker_names(config: ClusterConfig, active_nodes: int) -> list[str]:
    workers = config.worker_names()
    if not workers:
        return [f"worker-{index}" for index in range(1, active_nodes + 1)]
    if active_nodes <= len(workers):
        return workers[:active_nodes]
    synthetic: list[str] = list(workers)
    start = len(synthetic) + 1
    for index in range(start, active_nodes + 1):
        synthetic.append(f"worker-{index}")
    return synthetic


def _scaling_node_name(config: ClusterConfig, action: str, current: int, desired: int) -> str:
    workers = _active_worker_names(config, max(current, desired))
    if action == "scale_up" and desired > 0:
        return workers[desired - 1]
    if action == "scale_down" and current > 0:
        return workers[current - 1]
    return "none"


def _normalize_role(value: object) -> str:
    role = str(value or "").strip().lower()
    if role in {"controller", "worker"}:
        return role
    raise Namel3ssError(_invalid_role_message())


def _require_text(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    if text:
        return text
    raise Namel3ssError(_missing_field_message(field_name))


def _normalize_int(value: object, *, field_name: str, minimum: int) -> int:
    if isinstance(value, bool):
        raise Namel3ssError(_invalid_int_message(field_name))
    try:
        parsed = int(value)
    except Exception as err:
        raise Namel3ssError(_invalid_int_message(field_name)) from err
    if parsed < minimum:
        raise Namel3ssError(_invalid_int_message(field_name))
    return parsed


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _next_step(events: tuple[dict[str, object], ...]) -> int:
    if not events:
        return 1
    return max(int(item.get("step_count") or 0) for item in events) + 1


def _missing_config_message(path: str) -> str:
    return build_guidance_message(
        what="Cluster config is missing.",
        why=f"Expected {path}.",
        fix="Create cluster.yaml before running cluster commands.",
        example=(
            "cluster:\n"
            "  nodes:\n"
            "    - name: node1\n"
            "      host: 10.0.0.1\n"
            "      role: controller\n"
            "      capacity: 4cores-8GB"
        ),
    )


def _invalid_config_message(path: Path, detail: str) -> str:
    return build_guidance_message(
        what="Cluster config is invalid.",
        why=f"{path.as_posix()} could not be parsed: {detail}.",
        fix="Fix cluster.yaml fields and retry.",
        example="cluster:\n  scaling_policy:\n    target_cpu_percent: 70\n    max_nodes: 5\n    min_nodes: 2",
    )


def _invalid_state_message(path: Path) -> str:
    return build_guidance_message(
        what="Cluster state is invalid.",
        why=f"{path.as_posix()} contains malformed state JSON.",
        fix="Repair or remove the state file.",
        example="rm .namel3ss/cluster_state.json",
    )


def _invalid_int_message(field_name: str) -> str:
    return build_guidance_message(
        what=f"{field_name} is invalid.",
        why="Expected a positive integer.",
        fix=f"Set {field_name} to a valid integer.",
        example=f"{field_name}: 1",
    )


def _invalid_role_message() -> str:
    return build_guidance_message(
        what="Cluster node role is invalid.",
        why="role must be controller or worker.",
        fix="Set role to controller or worker.",
        example="role: worker",
    )


def _missing_field_message(field_name: str) -> str:
    return build_guidance_message(
        what=f"{field_name} is required.",
        why="Cluster nodes need complete metadata.",
        fix=f"Set {field_name} in cluster.yaml.",
        example=f"{field_name}: node1",
    )


def _invalid_version_message() -> str:
    return build_guidance_message(
        what="Cluster deploy version is missing.",
        why="deploy requires a runtime version string.",
        fix="Pass a version after cluster deploy.",
        example="n3 cluster deploy 1.2.0",
    )


__all__ = [
    "CLUSTER_FILENAME",
    "ClusterConfig",
    "ClusterNode",
    "ClusterPolicy",
    "ClusterRollingUpdate",
    "cluster_path",
    "cluster_state_path",
    "cluster_status",
    "deploy_cluster",
    "load_cluster_config",
    "load_cluster_state",
    "save_cluster_config",
    "scale_cluster",
]
