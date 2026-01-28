from __future__ import annotations

from functools import lru_cache

from namel3ss.ir.functions.model import FunctionParam, FunctionSignature
from namel3ss.ir.model.contracts import ContractDecl


def pipeline_contracts() -> dict[str, ContractDecl]:
    return dict(_PIPELINE_CONTRACTS())


@lru_cache(maxsize=1)
def _PIPELINE_CONTRACTS() -> dict[str, ContractDecl]:
    return {
        "ingestion": ContractDecl(
            kind="pipeline",
            name="ingestion",
            signature=FunctionSignature(
                inputs=[
                    _field("upload_id", "text", required=True),
                    _field("mode", "text", required=False),
                    _field("ingestion", "json", required=False),
                    _field("index", "json", required=False),
                ],
                outputs=[
                    _field("report", "json", required=True),
                    _field("ingestion", "json", required=True),
                    _field("index", "json", required=True),
                ],
                line=None,
                column=None,
            ),
            line=None,
            column=None,
        ),
        "retrieval": ContractDecl(
            kind="pipeline",
            name="retrieval",
            signature=FunctionSignature(
                inputs=[
                    _field("query", "text", required=False),
                    _field("limit", "number", required=False),
                    _field("ingestion", "json", required=False),
                    _field("index", "json", required=False),
                ],
                outputs=[
                    _field("report", "json", required=True),
                ],
                line=None,
                column=None,
            ),
            line=None,
            column=None,
        ),
    }


def _field(name: str, type_name: str, *, required: bool) -> FunctionParam:
    return FunctionParam(name=name, type_name=type_name, required=required, line=None, column=None)


__all__ = ["pipeline_contracts"]
