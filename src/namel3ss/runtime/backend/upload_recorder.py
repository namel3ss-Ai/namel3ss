from __future__ import annotations

from dataclasses import dataclass, field

from namel3ss.errors.contract import build_error_entry
from namel3ss.runtime.backend.upload_contract import (
    UPLOAD_PROGRESS_STEP_BYTES,
    UPLOAD_STATE_ACCEPTED,
    UPLOAD_STATE_RECEIVING,
    UPLOAD_STATE_REJECTED,
    UPLOAD_STATE_STORED,
    UPLOAD_STATE_VALIDATED,
    UploadProgressTracker,
)
from namel3ss.runtime.backend.studio_effect_adapter_uploads import (
    record_upload_error,
    record_upload_preview,
    record_upload_progress,
    record_upload_received,
    record_upload_state,
    record_upload_stored,
)


RECOVERY_ACTIONS = ["retry", "remove"]


@dataclass
class UploadRecorder:
    total_bytes: int | None = None
    step_bytes: int = UPLOAD_PROGRESS_STEP_BYTES
    traces: list[dict] = field(default_factory=list)
    _progress: UploadProgressTracker = field(init=False)
    _name: str | None = None
    _content_type: str | None = None
    _state: str | None = None
    _error: dict | None = None
    _preview: dict | None = None
    _receiving: bool = False

    def __post_init__(self) -> None:
        self._progress = UploadProgressTracker(self.total_bytes, step_bytes=self.step_bytes)

    def set_total_bytes(self, total_bytes: int | None) -> None:
        self._progress.set_total_bytes(total_bytes)

    def accept(self, *, name: str, content_type: str | None) -> None:
        self._name = name
        self._content_type = content_type
        self._state = UPLOAD_STATE_ACCEPTED
        record_upload_state(
            self.traces,
            name=self._name,
            state=self._state,
            progress=self._progress.snapshot(),
        )

    def advance(self, amount: int) -> None:
        if amount <= 0:
            return
        if not self._receiving:
            self._receiving = True
            self._state = UPLOAD_STATE_RECEIVING
            record_upload_state(
                self.traces,
                name=self._name,
                state=self._state,
                progress=self._progress.snapshot(),
            )
        for progress in self._progress.advance(amount):
            record_upload_progress(self.traces, name=self._name, progress=progress)

    def record_success(self, metadata: dict) -> None:
        self._name = _text_value(metadata.get("name"), self._name or "upload")
        self._content_type = _text_value(metadata.get("content_type"), self._content_type or "")
        self._emit_progress(completed=True)
        self._state = UPLOAD_STATE_VALIDATED
        record_upload_state(
            self.traces,
            name=self._name,
            state=self._state,
            progress=self._progress.snapshot(),
        )
        preview = metadata.get("preview")
        if isinstance(preview, dict):
            self._preview = dict(preview)
            record_upload_preview(self.traces, name=self._name, preview=self._preview)
        record_upload_received(
            self.traces,
            name=_text_value(metadata.get("name"), "upload"),
            content_type=_text_value(metadata.get("content_type"), ""),
            bytes_len=_int_value(metadata.get("bytes")),
            checksum=_text_value(metadata.get("checksum"), ""),
        )
        record_upload_stored(
            self.traces,
            name=_text_value(metadata.get("name"), "upload"),
            stored_path=_text_value(metadata.get("stored_path"), ""),
        )
        self._state = UPLOAD_STATE_STORED
        record_upload_state(
            self.traces,
            name=self._name,
            state=self._state,
            progress=self._progress.snapshot(),
        )

    def record_error(
        self,
        err: Exception,
        *,
        project_root: str | None = None,
        secret_values: list[str] | None = None,
    ) -> None:
        self._emit_progress(completed=False)
        entry = build_error_entry(
            error=err,
            error_payload=None,
            error_pack=None,
            project_root=project_root,
            secret_values=secret_values,
        )
        self._error = _error_payload(entry)
        record_upload_error(self.traces, name=self._name, error=self._error)
        self._state = UPLOAD_STATE_REJECTED
        record_upload_state(
            self.traces,
            name=self._name,
            state=self._state,
            progress=self._progress.snapshot(),
            error=self._error,
        )

    def build_upload_payload(self, metadata: dict | None = None) -> dict:
        payload = dict(metadata or {})
        if self._name and "name" not in payload:
            payload["name"] = self._name
        if self._content_type and "content_type" not in payload:
            payload["content_type"] = self._content_type
        if self._preview and "preview" not in payload:
            payload["preview"] = dict(self._preview)
        if self._state:
            payload["state"] = self._state
        payload["progress"] = self._progress.snapshot()
        if self._error:
            payload["error"] = dict(self._error)
        return payload

    def _emit_progress(self, *, completed: bool) -> None:
        for progress in self._progress.finalize(completed=completed):
            record_upload_progress(self.traces, name=self._name, progress=progress)


def _error_payload(entry: dict) -> dict:
    code = _text_value(entry.get("code"), "upload_error")
    message = _text_value(entry.get("message"), "Upload failed.")
    reason = _text_value(entry.get("hint"), message)
    error: dict[str, object] = {
        "code": code,
        "reason": reason,
        "recovery_actions": list(RECOVERY_ACTIONS),
    }
    if message:
        error["message"] = message
    remediation = entry.get("remediation")
    if isinstance(remediation, str) and remediation:
        error["remediation"] = remediation
    return error


def _int_value(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return 0


def _text_value(value: object, default: str) -> str:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned if cleaned else default
    return default


def apply_upload_error_payload(payload: dict, recorder: UploadRecorder) -> dict:
    if not isinstance(payload, dict):
        return payload
    payload["upload"] = recorder.build_upload_payload()
    payload["traces"] = list(recorder.traces)
    return payload


__all__ = ["UploadRecorder", "apply_upload_error_payload"]
