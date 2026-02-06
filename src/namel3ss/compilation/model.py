from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


TARGET_C = "c"
TARGET_PYTHON = "python"
TARGET_RUST = "rust"
TARGET_WASM = "wasm"
SUPPORTED_TARGETS = (TARGET_C, TARGET_PYTHON, TARGET_RUST, TARGET_WASM)


@dataclass(frozen=True)
class CompilationConfig:
    flows: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {
            "flows": {
                name: self.flows[name]
                for name in sorted(self.flows.keys(), key=str)
            }
        }


@dataclass(frozen=True)
class CompiledModule:
    flow_name: str
    language: str
    artifact_path: str
    header_path: str | None
    version: str
    source_only: bool

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "flow_name": self.flow_name,
            "language": self.language,
            "artifact_path": self.artifact_path,
            "version": self.version,
            "source_only": self.source_only,
        }
        if self.header_path:
            payload["header_path"] = self.header_path
        return payload


class NumericExpr:
    pass


@dataclass(frozen=True)
class NumberLiteral(NumericExpr):
    text: str


@dataclass(frozen=True)
class InputNumber(NumericExpr):
    key: str


@dataclass(frozen=True)
class LocalNumber(NumericExpr):
    name: str


@dataclass(frozen=True)
class UnaryNumber(NumericExpr):
    op: str
    operand: NumericExpr


@dataclass(frozen=True)
class BinaryNumber(NumericExpr):
    op: str
    left: NumericExpr
    right: NumericExpr


@dataclass(frozen=True)
class NumericAssignment:
    name: str
    expr: NumericExpr


@dataclass(frozen=True)
class NumericFlowPlan:
    flow_name: str
    assignments: tuple[NumericAssignment, ...]
    result: NumericExpr
    input_keys: tuple[str, ...]


@dataclass(frozen=True)
class GeneratedProject:
    flow_name: str
    language: str
    root: Path
    artifact: Path
    header: Path | None
    files: tuple[Path, ...]
    build_command: tuple[str, ...] | None


__all__ = [
    "BinaryNumber",
    "CompilationConfig",
    "CompiledModule",
    "GeneratedProject",
    "InputNumber",
    "LocalNumber",
    "NumberLiteral",
    "NumericAssignment",
    "NumericExpr",
    "NumericFlowPlan",
    "SUPPORTED_TARGETS",
    "TARGET_C",
    "TARGET_PYTHON",
    "TARGET_RUST",
    "TARGET_WASM",
    "UnaryNumber",
]
