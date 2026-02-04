from __future__ import annotations

from namel3ss.config.loader import load_config
from namel3ss.config.model import AppConfig
from namel3ss.ingestion.hash import hash_chunk
from namel3ss.runtime.embeddings.service import embed_text, embedding_enabled, resolve_embedding_model
from namel3ss.runtime.embeddings.store import EmbeddingRecord, get_embedding_store


def store_chunk_embeddings(
    chunks: list[dict],
    *,
    upload_id: str,
    config: AppConfig | None,
    project_root: str | None,
    app_path: str | None,
    capabilities: tuple[str, ...] | list[str] | None,
) -> dict:
    if not embedding_enabled(capabilities):
        return {"enabled": False, "stored": 0, "cached": 0, "model_id": None}
    cfg = config or load_config(
        app_path=app_path if isinstance(app_path, str) else None,
        root=project_root if isinstance(project_root, str) else None,
    )
    model = resolve_embedding_model(cfg)
    store = get_embedding_store(cfg, project_root=project_root, app_path=app_path)
    candidates: list[tuple[str, str, str]] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        if chunk.get("ingestion_phase") != "deep":
            continue
        chunk_index = chunk.get("chunk_index")
        page_number = chunk.get("page_number")
        if not isinstance(chunk_index, int) or not isinstance(page_number, int):
            continue
        chunk_hash = chunk.get("chunk_hash")
        if not isinstance(chunk_hash, str) or not chunk_hash:
            chunk_hash = hash_chunk(
                document_id=upload_id,
                page_number=page_number,
                chunk_index=chunk_index,
                text=str(chunk.get("text") or ""),
            )
        chunk_id = f"{upload_id}:{chunk_index}"
        candidates.append((chunk_id, chunk_hash, str(chunk.get("text") or "")))
    if not candidates:
        return {"enabled": True, "stored": 0, "cached": 0, "model_id": model.model_id}
    existing = store.get_records(model_id=model.model_id, chunk_hashes=[item[1] for item in candidates])
    records: list[EmbeddingRecord] = []
    for chunk_id, chunk_hash, text in candidates:
        if chunk_hash in existing:
            continue
        try:
            vector = embed_text(text, model)
            status = "ok"
        except Exception:
            vector = None
            status = "unavailable"
        records.append(
            EmbeddingRecord(
                chunk_id=chunk_id,
                chunk_hash=chunk_hash,
                model_id=model.model_id,
                dims=model.dims,
                vector=vector,
                status=status,
            )
        )
    if records:
        store.write_records(records)
    return {
        "enabled": True,
        "stored": len(records),
        "cached": len(existing),
        "model_id": model.model_id,
    }


__all__ = ["store_chunk_embeddings"]
