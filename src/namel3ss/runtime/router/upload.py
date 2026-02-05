from __future__ import annotations

from types import SimpleNamespace

from namel3ss.persistence.dataset_inference import infer_dataset_schema
from namel3ss.persistence.local_store import LocalStore
from namel3ss.runtime.backend.upload_handler import handle_upload
from namel3ss.runtime.backend.upload_recorder import UploadRecorder


def handle_route_upload(headers: dict[str, str], rfile, program) -> dict:
    length_header = headers.get("Content-Length") or headers.get("content-length")
    content_length = None
    if length_header:
        try:
            content_length = int(length_header)
        except ValueError:
            content_length = None
    upload_name = headers.get("X-Upload-Name") or headers.get("x-upload-name")
    ctx = SimpleNamespace(
        capabilities=getattr(program, "capabilities", ()) or (),
        project_root=getattr(program, "project_root", None),
        app_path=getattr(program, "app_path", None),
    )
    recorder = UploadRecorder()
    response = handle_upload(
        ctx,
        headers=headers,
        rfile=rfile,
        content_length=content_length,
        upload_name=upload_name,
        recorder=recorder,
    )
    return response.get("upload") if isinstance(response, dict) else {}


def register_dataset(metadata: dict, program, identity: dict | None, auth_context: object | None) -> None:
    upload_id = metadata.get("checksum")
    if not isinstance(upload_id, str) or not upload_id:
        return
    store = LocalStore(getattr(program, "project_root", None), getattr(program, "app_path", None))
    existing = store.load_datasets()
    for entry in existing:
        if entry.get("dataset_id") == upload_id:
            entry["owner"] = _resolve_owner(identity, auth_context)
            store.save_datasets(existing)
            return
    path = store.upload_path_for(upload_id)
    if not path.exists():
        return
    schema = infer_dataset_schema(
        filename=metadata.get("name"),
        content_type=metadata.get("content_type"),
        data=path.read_bytes(),
    )
    if not schema:
        return
    owner = _resolve_owner(identity, auth_context)
    dataset = {
        "dataset_id": upload_id,
        "name": metadata.get("name") or upload_id,
        "schema": schema,
        "source": upload_id,
        "owner": owner,
    }
    store.upsert_dataset(dataset)


def _resolve_owner(identity: dict | None, auth_context: object | None) -> str:
    if isinstance(identity, dict):
        for key in ("id", "email", "name"):
            value = identity.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    auth_identity = getattr(auth_context, "identity", None)
    if isinstance(auth_identity, dict):
        for key in ("id", "email", "name"):
            value = auth_identity.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return "anonymous"


__all__ = ["handle_route_upload", "register_dataset"]
