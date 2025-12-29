from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from namel3ss.spec_check.model import SpecDecision, SpecPack


def normalize_decision(decision: SpecDecision) -> SpecDecision:
    return SpecDecision(
        status=decision.status,
        declared_spec=decision.declared_spec,
        engine_supported=normalize_list(decision.engine_supported),
        required_capabilities=normalize_list(decision.required_capabilities),
        unsupported_capabilities=normalize_list(decision.unsupported_capabilities),
        what=decision.what,
        why=normalize_bullets(decision.why),
        fix=normalize_bullets(decision.fix),
        example=decision.example,
    )


def normalize_list(items: Iterable[str]) -> tuple[str, ...]:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    return tuple(sorted(dict.fromkeys(cleaned)))


def normalize_bullets(items: Iterable[str]) -> tuple[str, ...]:
    return normalize_list(items)


def write_spec_artifacts(root: Path, pack: SpecPack, plain_text: str, when_text: str) -> None:
    spec_dir = root / ".namel3ss" / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "last.json").write_text(_stable_json(pack.as_dict()), encoding="utf-8")
    (spec_dir / "last.plain").write_text(plain_text.rstrip() + "\n", encoding="utf-8")
    (spec_dir / "last.when.txt").write_text(when_text.rstrip() + "\n", encoding="utf-8")


def _stable_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


__all__ = ["normalize_decision", "normalize_bullets", "normalize_list", "write_spec_artifacts"]
