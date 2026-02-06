from __future__ import annotations

from dataclasses import asdict

from namel3ss.cir.model import CIRProgram
from namel3ss.determinism import canonical_json_dumps


def cir_to_payload(program: CIRProgram) -> dict[str, object]:
    return asdict(program)


def cir_to_json(program: CIRProgram, *, pretty: bool = True) -> str:
    payload = cir_to_payload(program)
    return canonical_json_dumps(payload, pretty=pretty, drop_run_keys=False)


__all__ = ["cir_to_json", "cir_to_payload"]
