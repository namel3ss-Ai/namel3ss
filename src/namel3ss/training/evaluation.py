from __future__ import annotations

import hashlib
from typing import Iterable

from namel3ss.determinism import canonical_json_dumps


def evaluate_validation_rows(
    *,
    modality: str,
    seed: int,
    artifact_checksum: str,
    rows: Iterable[dict[str, object]],
) -> dict[str, float]:
    values = list(rows)
    if not values:
        if modality == "audio":
            return {"transcript_accuracy": 0.0, "wer": 1.0}
        if modality == "image":
            return {"accuracy": 0.0, "caption_score": 0.0}
        return {"accuracy": 0.0, "bleu": 0.0}

    matches: list[float] = []
    scores: list[float] = []
    token_overlaps: list[float] = []
    word_error_rates: list[float] = []

    for row in values:
        row_json = canonical_json_dumps(row, pretty=False, drop_run_keys=False)
        digest = hashlib.sha256(f"{artifact_checksum}:{seed}:{row_json}".encode("utf-8")).hexdigest()

        target = _target_text(row)
        predicted = _predict_text(target=target, digest=digest)

        match = 1.0 if target and predicted == target else 0.0
        overlap = _token_overlap(predicted, target)
        wer = _word_error_rate(predicted, target)
        score = (int(digest[:8], 16) % 1000) / 1000.0

        matches.append(match)
        scores.append(score)
        token_overlaps.append(overlap)
        word_error_rates.append(wer)

    accuracy = _round(_avg(matches))

    if modality == "image":
        return {
            "accuracy": accuracy,
            "caption_score": _round(_avg(scores)),
        }
    if modality == "audio":
        return {
            "transcript_accuracy": accuracy,
            "wer": _round(_avg(word_error_rates)),
        }
    return {
        "accuracy": accuracy,
        "bleu": _round(_avg(token_overlaps)),
    }


def _target_text(row: dict[str, object]) -> str:
    for key in ("target", "label", "transcript", "output"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    value = row.get("input")
    if isinstance(value, str):
        return value.strip()
    return ""


def _predict_text(*, target: str, digest: str) -> str:
    if target and int(digest[:2], 16) % 3 == 0:
        return target
    token = digest[:12]
    return f"pred_{token}"


def _token_overlap(predicted: str, target: str) -> float:
    if not predicted or not target:
        return 0.0
    predicted_tokens = [token for token in predicted.lower().split() if token]
    target_tokens = [token for token in target.lower().split() if token]
    if not predicted_tokens or not target_tokens:
        return 0.0
    intersection = set(predicted_tokens).intersection(target_tokens)
    return len(intersection) / max(len(target_tokens), 1)


def _word_error_rate(predicted: str, target: str) -> float:
    if not target:
        return 0.0
    pred_tokens = [token for token in predicted.lower().split() if token]
    tgt_tokens = [token for token in target.lower().split() if token]
    if not tgt_tokens:
        return 0.0
    edits = _edit_distance(pred_tokens, tgt_tokens)
    return min(1.0, edits / len(tgt_tokens))


def _edit_distance(a: list[str], b: list[str]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, token_a in enumerate(a, start=1):
        curr = [i]
        for j, token_b in enumerate(b, start=1):
            cost = 0 if token_a == token_b else 1
            curr.append(min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _round(value: float) -> float:
    return round(value, 6)


__all__ = ["evaluate_validation_rows"]
