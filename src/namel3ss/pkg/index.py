from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.request import urlopen

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


INDEX_SCHEMA_VERSION = 1
INDEX_PATH_ENV = "N3_PKG_INDEX_PATH"
INDEX_URL_ENV = "N3_PKG_INDEX_URL"
DEFAULT_INDEX_PATH = Path(__file__).resolve().parents[3] / "resources" / "pkg_index_v1.json"

TRUST_ORDER = {
    "official": 0,
    "verified": 1,
    "community": 2,
}


@dataclass(frozen=True)
class IndexEntry:
    name: str
    description: str
    source: str
    recommended: str
    license: str
    checksums: str
    tags: list[str]
    trust_tier: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "recommended": self.recommended,
            "license": self.license,
            "checksums": self.checksums,
            "tags": list(self.tags),
            "trust_tier": self.trust_tier,
        }

    def source_spec(self) -> str:
        if self.source.startswith("github:") and "@" in self.source:
            return self.source
        ref = self.recommended or "main"
        if self.source.startswith("github:"):
            base = self.source
        else:
            base = f"github:{self.source}"
        if "@" in base:
            return base
        return f"{base}@{ref}"


@dataclass(frozen=True)
class SearchResult:
    entry: IndexEntry
    matched_tokens: list[str]
    score: int

    def to_dict(self) -> dict:
        payload = self.entry.to_dict()
        payload["matched_tokens"] = list(self.matched_tokens)
        payload["score"] = self.score
        payload["install"] = f"n3 pkg add {self.entry.source_spec()}"
        return payload


def load_index(path: Path | None = None) -> list[IndexEntry]:
    data = _read_index_data(path)
    errors = validate_index_data(data)
    if errors:
        raise Namel3ssError(
            build_guidance_message(
                what="Package index is invalid.",
                why="; ".join(errors),
                fix="Fix the index JSON schema.",
                example="resources/pkg_index_v1.json",
            )
        )
    entries = [_entry_from_dict(entry) for entry in data.get("entries", [])]
    return sorted(entries, key=lambda item: item.name)


def search_index(query: str, entries: Iterable[IndexEntry]) -> list[SearchResult]:
    tokens = _tokenize(query)
    results: list[SearchResult] = []
    for entry in entries:
        score, matched = _score_entry(entry, tokens)
        if score <= 0:
            continue
        results.append(SearchResult(entry=entry, matched_tokens=matched, score=score))
    return sorted(
        results,
        key=lambda item: (
            TRUST_ORDER.get(item.entry.trust_tier, 9),
            -item.score,
            item.entry.name,
        ),
    )


def get_entry(name: str, entries: Iterable[IndexEntry]) -> IndexEntry | None:
    needle = name.strip().lower()
    for entry in entries:
        if entry.name.lower() == needle:
            return entry
    return None


def validate_index_data(data: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["index must be a JSON object"]
    if data.get("schema_version") != INDEX_SCHEMA_VERSION:
        errors.append("schema_version must be 1")
    entries = data.get("entries")
    if not isinstance(entries, list):
        return errors + ["entries must be a list"]
    for idx, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            errors.append(f"entry {idx} must be an object")
            continue
        errors.extend(_validate_entry(entry, idx))
    return errors


def _validate_entry(entry: dict, idx: int) -> list[str]:
    errors: list[str] = []
    required = {
        "name",
        "description",
        "source",
        "recommended",
        "license",
        "checksums",
        "tags",
        "trust_tier",
    }
    missing = required - set(entry.keys())
    if missing:
        errors.append(f"entry {idx} missing fields: {', '.join(sorted(missing))}")
        return errors
    for key in ("name", "description", "source", "recommended", "license", "checksums", "trust_tier"):
        if not isinstance(entry.get(key), str) or not entry.get(key):
            errors.append(f"entry {idx} {key} must be a non-empty string")
    tags = entry.get("tags")
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        errors.append(f"entry {idx} tags must be a list of strings")
    trust = entry.get("trust_tier")
    if isinstance(trust, str) and trust not in TRUST_ORDER:
        errors.append(f"entry {idx} trust_tier must be official, verified, or community")
    return errors


def _read_index_data(path: Path | None) -> dict:
    if path is None:
        env_path = os.getenv(INDEX_PATH_ENV, "").strip()
        if env_path:
            path = Path(env_path)
        else:
            env_url = os.getenv(INDEX_URL_ENV, "").strip()
            if env_url:
                return _read_index_url(env_url)
            path = DEFAULT_INDEX_PATH
    if not path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="Package index file was not found.",
                why=f"Expected {path.as_posix()} to exist.",
                fix="Set N3_PKG_INDEX_PATH or restore the default index.",
                example="resources/pkg_index_v1.json",
            )
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Package index is not valid JSON.",
                why=f"JSON parsing failed: {err.msg}.",
                fix="Fix the JSON formatting.",
                example="resources/pkg_index_v1.json",
            )
        ) from err


def _read_index_url(url: str) -> dict:
    try:
        with urlopen(url, timeout=5) as resp:
            data = resp.read().decode("utf-8")
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Package index could not be fetched.",
                why=str(err),
                fix="Check the index URL or use a local index file.",
                example="N3_PKG_INDEX_URL=https://.../index.json",
            )
        ) from err
    try:
        payload = json.loads(data)
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Package index response is not valid JSON.",
                why=f"JSON parsing failed: {err.msg}.",
                fix="Fix the index file content.",
                example="index.json",
            )
        ) from err
    return payload if isinstance(payload, dict) else {}


def _entry_from_dict(entry: dict) -> IndexEntry:
    return IndexEntry(
        name=str(entry.get("name") or ""),
        description=str(entry.get("description") or ""),
        source=str(entry.get("source") or ""),
        recommended=str(entry.get("recommended") or ""),
        license=str(entry.get("license") or ""),
        checksums=str(entry.get("checksums") or ""),
        tags=sorted({str(tag) for tag in (entry.get("tags") or []) if str(tag)}),
        trust_tier=str(entry.get("trust_tier") or "community"),
    )


def _score_entry(entry: IndexEntry, tokens: list[str]) -> tuple[int, list[str]]:
    if not tokens:
        return 1, []
    haystack = " ".join([entry.name, entry.description, " ".join(entry.tags)]).lower()
    score = 0
    matched: list[str] = []
    for token in tokens:
        if token in haystack:
            score += 2 if token in entry.name.lower() else 1
            matched.append(token)
    return score, matched


def _tokenize(query: str) -> list[str]:
    return [token for token in (query or "").lower().replace("-", " ").split() if token]


__all__ = [
    "INDEX_SCHEMA_VERSION",
    "IndexEntry",
    "SearchResult",
    "get_entry",
    "load_index",
    "search_index",
    "validate_index_data",
]
