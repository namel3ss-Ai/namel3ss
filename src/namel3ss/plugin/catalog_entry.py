from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtensionCatalogEntry:
    name: str
    version: str
    author: str
    description: str
    permissions: tuple[str, ...]
    hooks: tuple[tuple[str, str], ...]
    min_api_version: int
    signature: str | None
    tags: tuple[str, ...]
    rating: float | None
    digest: str
    source_path: str
    trusted: bool
    download_url: str | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "permissions": list(self.permissions),
            "hooks": {key: value for key, value in self.hooks},
            "min_api_version": self.min_api_version,
            "signature": self.signature,
            "tags": list(self.tags),
            "rating": self.rating,
            "hash": self.digest,
            "source_path": self.source_path,
            "trusted": self.trusted,
            "download_url": self.download_url,
        }


__all__ = ["ExtensionCatalogEntry"]
