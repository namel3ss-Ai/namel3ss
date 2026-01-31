from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

from namel3ss.observability.log_store import LogStore
from namel3ss.observability.metrics_store import MetricsStore
from namel3ss.observability.scrub import scrub_payload, scrub_text
from namel3ss.observability.trace_store import TraceStore
from namel3ss.secrets import collect_secret_values


class ObservabilityContext:
    def __init__(
        self,
        *,
        project_root: str | Path | None,
        app_path: str | Path | None,
        secret_values: Iterable[str] | None = None,
    ) -> None:
        self.project_root = project_root
        self.app_path = app_path
        self.secret_values = list(secret_values or [])
        self._scrub = lambda value: scrub_payload(
            value,
            secret_values=self.secret_values,
            project_root=self.project_root,
            app_path=self.app_path,
        )
        self._timing_specs: dict[str, tuple[str, dict]] = {}
        self._logical_counter = 0
        self.logs = LogStore(project_root=project_root, app_path=app_path, scrubber=self._scrub)
        self.traces = TraceStore(project_root=project_root, app_path=app_path, scrubber=self._scrub)
        self.metrics = MetricsStore(project_root=project_root, app_path=app_path, scrubber=self._scrub)

    @classmethod
    def from_config(
        cls,
        *,
        project_root: str | Path | None,
        app_path: str | Path | None,
        config=None,
    ) -> "ObservabilityContext":
        return cls(
            project_root=project_root,
            app_path=app_path,
            secret_values=collect_secret_values(config),
        )

    def start_session(self) -> None:
        self.logs.reset()
        self.traces.reset()
        self.metrics.reset()
        self._timing_specs = {}
        self._logical_counter = 0

    def record_log(self, *, level: str, message: object, fields: object | None = None) -> dict | None:
        span_id = self.traces.current_span_id()
        return self.logs.record(level=level, message=message, fields=fields, span_id=span_id)

    def record_event(self, *, name: str, kind: str, fields: object | None = None) -> dict | None:
        span_id = self.traces.current_span_id()
        return self.logs.record(
            level=kind,
            message=name,
            fields=fields,
            span_id=span_id,
            name=name,
            kind=kind,
        )

    def start_span(
        self,
        ctx,
        *,
        name: str,
        kind: str,
        details: dict | None = None,
        timing_name: str | None = None,
        timing_labels: dict | None = None,
        parent_id: str | None = None,
    ) -> str:
        span_id = self.traces.start_span(
            name=name,
            kind=kind,
            start_step=self._step(ctx),
            details=details,
            parent_id=parent_id,
        )
        if timing_name:
            clean_labels = timing_labels or {}
            self._timing_specs[span_id] = (timing_name, clean_labels)
        return span_id

    def end_span(self, ctx, span_id: str, *, status: str) -> None:
        span = self.traces.end_span(span_id, status=status, end_step=self._step(ctx))
        if not span:
            return
        timing = self._timing_specs.pop(span_id, None)
        if timing is None:
            return
        timing_name, timing_labels = timing
        duration = span.get("duration_steps")
        if isinstance(duration, int):
            self.metrics.record_timing(timing_name, duration=duration, labels=timing_labels)

    @contextmanager
    def span(
        self,
        ctx,
        *,
        name: str,
        kind: str,
        details: dict | None = None,
        timing_name: str | None = None,
        timing_labels: dict | None = None,
        parent_id: str | None = None,
    ):
        span_id = self.start_span(
            ctx,
            name=name,
            kind=kind,
            details=details,
            timing_name=timing_name,
            timing_labels=timing_labels,
            parent_id=parent_id,
        )
        try:
            yield span_id
        except Exception:
            self.end_span(ctx, span_id, status="error")
            raise
        else:
            self.end_span(ctx, span_id, status="ok")

    def flush(self) -> None:
        self.logs.flush()
        self.traces.flush()
        self.metrics.flush()

    def scrub_label_value(self, value: object) -> object:
        return scrub_payload(
            value,
            secret_values=self.secret_values,
            project_root=self.project_root,
            app_path=self.app_path,
        )

    def scrub_metric_name(self, name: str) -> str:
        return scrub_text(name, project_root=self.project_root, app_path=self.app_path)

    def _step(self, ctx) -> int:
        if ctx is None:
            self._logical_counter += 1
            return self._logical_counter
        value = getattr(ctx, "execution_step_counter", 0)
        try:
            return int(value)
        except Exception:
            return 0


__all__ = ["ObservabilityContext"]
