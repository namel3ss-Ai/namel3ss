from __future__ import annotations

from namel3ss.runtime.providers.pack_registry import list_provider_metadata


def provider_pack_catalog() -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for metadata in list_provider_metadata():
        rows.append(
            {
                "name": metadata.name,
                "capability_token": metadata.capability_token,
                "supported_modes": list(metadata.supported_modes),
                "models": list(metadata.models),
            }
        )
    rows.sort(key=lambda item: str(item.get("name") or ""))
    return tuple(rows)


__all__ = ["provider_pack_catalog"]
