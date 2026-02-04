from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import math
import re

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


@dataclass(frozen=True)
class EmbeddingModel:
    provider: str
    model: str
    version: str
    dims: int
    precision: int
    candidate_limit: int

    @property
    def model_id(self) -> str:
        return f"{self.provider}:{self.model}:{self.version}"


def embedding_enabled(capabilities: tuple[str, ...] | list[str] | None) -> bool:
    if not capabilities:
        return False
    return "embedding" in {str(item).strip().lower() for item in capabilities}


def resolve_embedding_model(config: AppConfig | None) -> EmbeddingModel:
    cfg = config or AppConfig()
    provider = _normalize_text(cfg.embedding.provider)
    model = _normalize_text(cfg.embedding.model)
    version = _normalize_text(cfg.embedding.version)
    dims = _coerce_positive_int(cfg.embedding.dims)
    precision = _coerce_non_negative_int(cfg.embedding.precision)
    candidate_limit = _coerce_positive_int(cfg.embedding.candidate_limit)
    if provider not in {"hash", "test"}:
        raise Namel3ssError(_provider_message(provider))
    if not model:
        raise Namel3ssError(_model_message("model"))
    if not version:
        raise Namel3ssError(_model_message("version"))
    if dims <= 0:
        raise Namel3ssError(_dims_message())
    if precision < 0:
        raise Namel3ssError(_precision_message())
    if candidate_limit <= 0:
        raise Namel3ssError(_candidate_limit_message())
    if provider == "test" and dims < 2:
        raise Namel3ssError(_dims_message(minimum=2))
    return EmbeddingModel(
        provider=provider,
        model=model,
        version=version,
        dims=dims,
        precision=precision,
        candidate_limit=candidate_limit,
    )


def embed_text(text: str | None, model: EmbeddingModel) -> list[float]:
    value = text if isinstance(text, str) else ""
    if model.provider == "hash":
        return _embed_hash(value, model)
    if model.provider == "test":
        return _embed_test(value, model)
    raise Namel3ssError(_provider_message(model.provider))


def vector_similarity(query: list[float], candidate: list[float], *, precision: int) -> float:
    if len(query) != len(candidate):
        raise Namel3ssError(_dims_mismatch_message(len(query), len(candidate)))
    if not query:
        return 0.0
    total = 0.0
    for left, right in zip(query, candidate):
        total += float(left) * float(right)
    return _round_value(total, precision)


def vector_is_zero(vector: list[float]) -> bool:
    return all(value == 0.0 for value in vector)


def _embed_hash(text: str, model: EmbeddingModel) -> list[float]:
    tokens = _tokenize(text)
    vector = [0.0] * model.dims
    if not tokens:
        return vector
    for token in tokens:
        digest = sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % model.dims
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[idx] += sign
    vector = _normalize(vector)
    return _round_vector(vector, model.precision)


def _embed_test(text: str, model: EmbeddingModel) -> list[float]:
    lowered = text.lower()
    if "fail" in lowered:
        raise ValueError("embedding test failure")
    vector = [0.0] * model.dims
    if "alpha" in lowered or "omega" in lowered:
        vector[0] = 1.0
    elif "beta" in lowered:
        vector[1] = 1.0
    else:
        vector[0] = 0.0
        if model.dims > 1:
            vector[1] = 0.0
    return _round_vector(_normalize(vector), model.precision)


def _normalize(vector: list[float]) -> list[float]:
    total = 0.0
    for value in vector:
        total += float(value) * float(value)
    if total <= 0.0:
        return vector
    denom = math.sqrt(total)
    return [float(value) / denom for value in vector]


def _round_vector(vector: list[float], precision: int) -> list[float]:
    return [_round_value(value, precision) for value in vector]


def _round_value(value: float, precision: int) -> float:
    quant = Decimal("1").scaleb(-precision)
    rounded = Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP)
    result = float(rounded)
    if result == 0.0:
        return 0.0
    return result


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]


def _normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _coerce_positive_int(value: object) -> int:
    if isinstance(value, bool):
        return -1
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except Exception:
        return -1


def _coerce_non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        return -1
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except Exception:
        return -1


def _provider_message(value: str) -> str:
    return build_guidance_message(
        what=f"Embedding provider '{value or ''}' is not supported.",
        why="Embedding providers must be hash or test.",
        fix="Set embedding.provider to a supported value.",
        example='[embedding]\nprovider = "hash"\nmodel = "hash"\nversion = "v1"',
    )


def _model_message(field: str) -> str:
    return build_guidance_message(
        what=f"Embedding {field} is missing.",
        why="Embeddings require a pinned model identity.",
        fix=f"Set embedding.{field} to a non-empty string.",
        example='[embedding]\nmodel = "hash"\nversion = "v1"',
    )


def _dims_message(minimum: int = 1) -> str:
    return build_guidance_message(
        what="Embedding dims must be a positive integer.",
        why="Embeddings require a fixed vector size.",
        fix=f"Set embedding.dims to an integer >= {minimum}.",
        example='[embedding]\ndims = 64',
    )


def _precision_message() -> str:
    return build_guidance_message(
        what="Embedding precision must be a non-negative integer.",
        why="Embedding scores are rounded deterministically.",
        fix="Set embedding.precision to 0 or a positive integer.",
        example='[embedding]\nprecision = 6',
    )


def _candidate_limit_message() -> str:
    return build_guidance_message(
        what="Embedding candidate_limit must be a positive integer.",
        why="Hybrid retrieval needs a stable candidate set size.",
        fix="Set embedding.candidate_limit to a positive integer.",
        example='[embedding]\ncandidate_limit = 50',
    )


def _dims_mismatch_message(expected: int, found: int) -> str:
    return build_guidance_message(
        what=f"Embedding vector dims mismatch (expected {expected}, found {found}).",
        why="Embeddings must be generated with a consistent model configuration.",
        fix="Ensure embedding model config matches stored vectors.",
        example='[embedding]\nmodel = "hash"\nversion = "v1"\ndims = 64',
    )


__all__ = [
    "EmbeddingModel",
    "embed_text",
    "embedding_enabled",
    "resolve_embedding_model",
    "vector_is_zero",
    "vector_similarity",
]
