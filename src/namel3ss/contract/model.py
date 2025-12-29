from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from namel3ss.ir.model.program import Program


CONTRACT_SPEC_VERSION = "contract.v1"


@dataclass(frozen=True)
class Contract:
    spec_version: str
    source_hash: str
    program: Program
    features_used: tuple[str, ...]
    capabilities_required: tuple[str, ...]
    flow_names: tuple[str, ...]

    def validate(self) -> None:
        from namel3ss.contract.api import validate_contract

        validate_contract(self)

    def run(
        self,
        flow: str,
        *,
        state: dict | None = None,
        input: dict | None = None,
        store=None,
        ai_provider=None,
        memory_manager=None,
        runtime_theme: str | None = None,
        identity: dict | None = None,
    ) -> "ExecutionResult":
        from namel3ss.contract.api import run_contract

        return run_contract(
            self,
            flow,
            state=state,
            input=input,
            store=store,
            ai_provider=ai_provider,
            memory_manager=memory_manager,
            runtime_theme=runtime_theme,
            identity=identity,
        )


@dataclass(frozen=True)
class ContractPack:
    spec_version: str
    source_hash: str
    program_summary: dict[str, object]
    features_used: list[str]
    capabilities_required: list[str]
    warnings: list[str]
    time_utc: str | None = None

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "spec_version": self.spec_version,
            "source_hash": self.source_hash,
            "program_summary": self.program_summary,
            "features_used": self.features_used,
            "capabilities_required": self.capabilities_required,
            "warnings": self.warnings,
        }
        if self.time_utc is not None:
            payload["time_utc"] = self.time_utc
        return payload


if TYPE_CHECKING:  # pragma: no cover - typing-only
    from namel3ss.runtime.executor.result import ExecutionResult


__all__ = ["CONTRACT_SPEC_VERSION", "Contract", "ContractPack"]
