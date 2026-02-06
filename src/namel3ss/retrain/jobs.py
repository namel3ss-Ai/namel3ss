from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from namel3ss.determinism import canonical_json_dump
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.mlops import get_mlops_client, load_mlops_config
from namel3ss.models import load_model_registry
from namel3ss.retrain.scheduler import build_retrain_payload
from namel3ss.runtime.persistence_paths import resolve_persistence_root


RETRAIN_JOBS_FILENAME = "retrain_jobs.json"
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass(frozen=True)
class RetrainJob:
    job_id: str
    model_name: str
    target_version: str
    training_dataset_version: str
    scheduled_at: int
    status: str
    backend: str
    result_uri: str | None
    metrics: dict[str, float]
    reason: str
    affected_flows: tuple[str, ...]
    feedback_weights: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "job_id": self.job_id,
            "model_name": self.model_name,
            "target_version": self.target_version,
            "training_dataset_version": self.training_dataset_version,
            "scheduled_at": int(self.scheduled_at),
            "status": self.status,
            "backend": self.backend,
            "metrics": {key: float(self.metrics[key]) for key in sorted(self.metrics.keys())},
            "reason": self.reason,
            "affected_flows": list(self.affected_flows),
            "feedback_weights": {
                key: float(self.feedback_weights[key]) for key in sorted(self.feedback_weights.keys())
            },
        }
        if self.result_uri:
            payload["result_uri"] = self.result_uri
        return payload


def retrain_jobs_path(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    allow_create: bool = True,
) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=allow_create)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / RETRAIN_JOBS_FILENAME


def list_retrain_jobs(project_root: str | Path | None, app_path: str | Path | None) -> list[dict[str, object]]:
    jobs = _load_jobs(project_root, app_path)
    return [item.to_dict() for item in jobs]


def schedule_retrain_jobs(project_root: str | Path | None, app_path: str | Path | None) -> dict[str, object]:
    retrain_payload = build_retrain_payload(project_root, app_path)
    suggestions = retrain_payload.get("suggestions")
    if not isinstance(suggestions, list):
        suggestions = []

    existing = _load_jobs(project_root, app_path)
    signatures = {_job_signature(item): item for item in existing if item.status in {"pending", "running"}}
    next_step = max([item.scheduled_at for item in existing], default=0)
    created: list[RetrainJob] = []
    feedback_weights = _feedback_weights(retrain_payload)
    backend = _default_backend(project_root, app_path)
    dataset_cache: dict[str, str] = {}

    for suggestion in _ordered_suggestions(suggestions):
        model_name = str(suggestion.get("model_name") or "").strip()
        reason = str(suggestion.get("reason") or "").strip() or "threshold_triggered"
        affected_flows = _normalize_flows(suggestion.get("affected_flows"))
        if not model_name:
            continue
        training_dataset_version = dataset_cache.get(model_name)
        if training_dataset_version is None:
            training_dataset_version = _dataset_version_for_model(project_root, app_path, model_name)
            dataset_cache[model_name] = training_dataset_version
        signature = f"{model_name}|{reason}|{training_dataset_version}"
        if signature in signatures:
            continue
        next_step += 1
        target_version = _next_target_version(project_root, app_path, existing + created, model_name)
        job = RetrainJob(
            job_id=f"job-{next_step:06d}",
            model_name=model_name,
            target_version=target_version,
            training_dataset_version=training_dataset_version,
            scheduled_at=next_step,
            status="pending",
            backend=backend,
            result_uri=None,
            metrics=_normalize_metrics(retrain_payload.get("metrics")),
            reason=reason,
            affected_flows=affected_flows,
            feedback_weights=feedback_weights,
        )
        created.append(job)
        signatures[signature] = job

    all_jobs = existing + created
    path = _save_jobs(project_root, app_path, all_jobs)
    result = dict(retrain_payload)
    result["jobs_path"] = path.as_posix() if path else None
    result["jobs"] = [item.to_dict() for item in created]
    result["scheduled_count"] = len(created)
    result["backend"] = backend
    result["mlops_configured"] = load_mlops_config(project_root, app_path, required=False) is not None
    return result


def run_retrain_job(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    job_id: str,
) -> dict[str, object]:
    target_job_id = str(job_id or "").strip()
    if not target_job_id:
        raise Namel3ssError(_invalid_job_id_message())
    jobs = _load_jobs(project_root, app_path)
    selected = next((item for item in jobs if item.job_id == target_job_id), None)
    if selected is None:
        raise Namel3ssError(_missing_job_message(target_job_id))
    if selected.status == "completed":
        return {"ok": True, "job": selected.to_dict(), "already_completed": True}

    result_uri = f"training://{selected.model_name}/{selected.target_version}/{selected.job_id}"
    mlops_payload = None
    client = get_mlops_client(project_root, app_path, required=False)
    if client is not None:
        mlops_payload = client.register_model(
            name=selected.model_name,
            version=selected.target_version,
            artifact_uri=result_uri,
            metrics=selected.metrics,
            experiment_id=selected.job_id,
            stage="candidate",
            dataset=selected.training_dataset_version,
        )

    updated = RetrainJob(
        job_id=selected.job_id,
        model_name=selected.model_name,
        target_version=selected.target_version,
        training_dataset_version=selected.training_dataset_version,
        scheduled_at=selected.scheduled_at,
        status="completed",
        backend=selected.backend,
        result_uri=result_uri,
        metrics=selected.metrics,
        reason=selected.reason,
        affected_flows=selected.affected_flows,
        feedback_weights=selected.feedback_weights,
    )
    saved: list[RetrainJob] = []
    for item in jobs:
        saved.append(updated if item.job_id == updated.job_id else item)
    path = _save_jobs(project_root, app_path, saved)
    payload = {"ok": True, "job": updated.to_dict(), "jobs_path": path.as_posix() if path else None}
    if mlops_payload is not None:
        payload["mlops"] = mlops_payload
    return payload


def _load_jobs(project_root: str | Path | None, app_path: str | Path | None) -> list[RetrainJob]:
    path = retrain_jobs_path(project_root, app_path, allow_create=False)
    if path is None or not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_jobs_message(path, str(err))) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_jobs_message(path, "expected an object"))
    items = payload.get("jobs")
    if not isinstance(items, list):
        raise Namel3ssError(_invalid_jobs_message(path, "jobs must be a list"))
    jobs: list[RetrainJob] = []
    for item in items:
        if not isinstance(item, dict):
            raise Namel3ssError(_invalid_jobs_message(path, "job entry must be an object"))
        jobs.append(_job_from_dict(item, path=path))
    return sorted(jobs, key=lambda entry: (entry.scheduled_at, entry.job_id))


def _save_jobs(project_root: str | Path | None, app_path: str | Path | None, jobs: list[RetrainJob]) -> Path | None:
    path = retrain_jobs_path(project_root, app_path)
    if path is None:
        return None
    payload = {"schema_version": 1, "jobs": [item.to_dict() for item in sorted(jobs, key=lambda e: (e.scheduled_at, e.job_id))]}
    canonical_json_dump(path, payload, pretty=True, drop_run_keys=False)
    return path


def _job_from_dict(raw: dict[str, object], *, path: Path) -> RetrainJob:
    job_id = str(raw.get("job_id") or "").strip()
    model_name = str(raw.get("model_name") or "").strip()
    target_version = str(raw.get("target_version") or "").strip()
    dataset_version = str(raw.get("training_dataset_version") or "").strip()
    status = str(raw.get("status") or "").strip()
    backend = str(raw.get("backend") or "").strip()
    reason = str(raw.get("reason") or "").strip()
    if not job_id or not model_name or not target_version or not dataset_version or not status or not backend:
        raise Namel3ssError(_invalid_jobs_message(path, "job entry is missing required fields"))
    try:
        scheduled_at = int(raw.get("scheduled_at"))
    except Exception as err:
        raise Namel3ssError(_invalid_jobs_message(path, "scheduled_at must be a number")) from err
    metrics = _normalize_metrics(raw.get("metrics"))
    feedback_weights = _normalize_weights(raw.get("feedback_weights"))
    affected_raw = raw.get("affected_flows")
    affected_flows = _normalize_flows(affected_raw)
    result_uri = str(raw.get("result_uri") or "").strip() or None
    return RetrainJob(
        job_id=job_id,
        model_name=model_name,
        target_version=target_version,
        training_dataset_version=dataset_version,
        scheduled_at=scheduled_at,
        status=status,
        backend=backend,
        result_uri=result_uri,
        metrics=metrics,
        reason=reason or "threshold_triggered",
        affected_flows=affected_flows,
        feedback_weights=feedback_weights,
    )


def _ordered_suggestions(suggestions: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        [item for item in suggestions if isinstance(item, dict)],
        key=lambda item: (
            str(item.get("model_name") or ""),
            str(item.get("reason") or ""),
            ",".join(_normalize_flows(item.get("affected_flows"))),
        ),
    )


def _normalize_metrics(value: object) -> dict[str, float]:
    metrics: dict[str, float] = {}
    if not isinstance(value, dict):
        return metrics
    feedback = value.get("feedback")
    ai = value.get("ai")
    for prefix, section in [("feedback", feedback), ("ai", ai)]:
        if not isinstance(section, dict):
            continue
        for key in sorted(section.keys()):
            raw = section.get(key)
            if isinstance(raw, bool):
                continue
            try:
                metrics[f"{prefix}.{key}"] = float(raw)
            except Exception:
                continue
    return metrics


def _normalize_weights(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    weights: dict[str, float] = {}
    for key in sorted(value.keys()):
        raw = value.get(key)
        try:
            weights[str(key)] = float(raw)
        except Exception:
            continue
    return weights


def _normalize_flows(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    flows: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            flows.append(text)
    return tuple(sorted(set(flows)))


def _job_signature(job: RetrainJob) -> str:
    return f"{job.model_name}|{job.reason}|{job.training_dataset_version}"


def _dataset_version_for_model(project_root: str | Path | None, app_path: str | Path | None, model_name: str) -> str:
    registry = load_model_registry(project_root, app_path)
    candidate = registry.find(model_name)
    training_dataset_version = getattr(candidate, "training_dataset_version", None) if candidate is not None else None
    if isinstance(training_dataset_version, str) and training_dataset_version.strip():
        return training_dataset_version.strip()
    return "feedback@latest"


def _next_target_version(
    project_root: str | Path | None,
    app_path: str | Path | None,
    jobs: list[RetrainJob],
    model_name: str,
) -> str:
    versions: list[tuple[int, int, int]] = []
    registry = load_model_registry(project_root, app_path)
    for entry in registry.entries:
        if entry.name != model_name:
            continue
        key = _parse_semver(entry.version)
        if key is not None:
            versions.append(key)
    for job in jobs:
        if job.model_name != model_name:
            continue
        key = _parse_semver(job.target_version)
        if key is not None:
            versions.append(key)
    if not versions:
        return "1.0.0"
    latest = sorted(versions)[-1]
    return f"{latest[0]}.{latest[1]}.{latest[2] + 1}"


def _parse_semver(value: str) -> tuple[int, int, int] | None:
    if not _SEMVER_RE.match(value):
        return None
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


def _default_backend(project_root: str | Path | None, app_path: str | Path | None) -> str:
    config = load_mlops_config(project_root, app_path, required=False)
    if config is None:
        return "manual"
    if config.training_backends:
        return config.training_backends[0]
    return config.tool


def _feedback_weights(payload: dict[str, object]) -> dict[str, float]:
    metrics = payload.get("metrics")
    feedback = metrics.get("feedback") if isinstance(metrics, dict) else None
    if not isinstance(feedback, dict):
        return {"excellent": 0.5, "good": 0.75, "bad": 1.25}
    total = float(feedback.get("total") or 0.0)
    bad = float(feedback.get("bad") or 0.0)
    bad_ratio = (bad / total) if total > 0 else 0.0
    return {
        "excellent": 0.5,
        "good": 0.75,
        "bad": round(1.0 + bad_ratio, 4),
    }


def _missing_job_message(job_id: str) -> str:
    return build_guidance_message(
        what=f"Retrain job {job_id} was not found.",
        why="The job id is missing from .namel3ss/retrain_jobs.json.",
        fix="List jobs first and then run one existing id.",
        example="n3 retrain list",
    )


def _invalid_job_id_message() -> str:
    return build_guidance_message(
        what="Retrain job id is missing.",
        why="run requires a job id.",
        fix="Provide a valid job id from n3 retrain list.",
        example="n3 retrain run job-000001",
    )


def _invalid_jobs_message(path: Path, details: str) -> str:
    return build_guidance_message(
        what="Retrain jobs file is invalid.",
        why=f"{path.as_posix()} could not be parsed: {details}.",
        fix="Delete the file and run n3 retrain schedule again.",
        example="n3 retrain schedule",
    )


__all__ = [
    "RETRAIN_JOBS_FILENAME",
    "RetrainJob",
    "list_retrain_jobs",
    "retrain_jobs_path",
    "run_retrain_job",
    "schedule_retrain_jobs",
]
