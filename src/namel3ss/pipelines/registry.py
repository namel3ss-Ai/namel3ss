from __future__ import annotations

from functools import lru_cache

from namel3ss.ir.functions.model import FunctionParam, FunctionSignature
from namel3ss.ir.model.contracts import ContractDecl
from namel3ss.pipelines.model import PipelineDefinition, PipelineStep, StepField


def pipeline_contracts() -> dict[str, ContractDecl]:
    return dict(_PIPELINE_CONTRACTS())


def pipeline_definitions() -> dict[str, PipelineDefinition]:
    return dict(_PIPELINE_DEFINITIONS())


def pipeline_purity(name: str) -> str:
    definition = pipeline_definitions().get(name)
    return definition.purity if definition is not None else "effectful"


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


@lru_cache(maxsize=1)
def _PIPELINE_DEFINITIONS() -> dict[str, PipelineDefinition]:
    return {
        "ingestion": PipelineDefinition(
            name="ingestion",
            purity="effectful",
            steps=(
                PipelineStep(
                    kind="accept",
                    summary_fields=(
                        StepField("upload_id", "text"),
                        StepField("content_type", "text"),
                        StepField("size", "number"),
                    ),
                ),
                PipelineStep(
                    kind="extract",
                    summary_fields=(
                        StepField("method_used", "text"),
                        StepField("detected_type", "text"),
                        StepField("text_chars", "number"),
                    ),
                ),
                PipelineStep(
                    kind="quality_gate",
                    summary_fields=(
                        StepField("status", "text"),
                        StepField("reasons", "json", required=False),
                    ),
                ),
                PipelineStep(
                    kind="chunk",
                    summary_fields=(
                        StepField("chunk_count", "number"),
                        StepField("chunk_chars", "number"),
                    ),
                ),
                PipelineStep(
                    kind="index",
                    summary_fields=(
                        StepField("indexed_chunks", "number"),
                        StepField("low_quality", "boolean"),
                    ),
                ),
                PipelineStep(
                    kind="report",
                    summary_fields=(
                        StepField("report_status", "text"),
                        StepField("report_checksum", "text"),
                    ),
                ),
            ),
        ),
        "retrieval": PipelineDefinition(
            name="retrieval",
            purity="effectful",
            steps=(
                PipelineStep(
                    kind="accept",
                    summary_fields=(
                        StepField("query", "text"),
                        StepField("limit", "json", required=False),
                    ),
                ),
                PipelineStep(
                    kind="select_sources",
                    summary_fields=(
                        StepField("excluded_blocked", "number"),
                        StepField("excluded_warn", "number"),
                        StepField("warn_allowed", "boolean"),
                    ),
                ),
                PipelineStep(
                    kind="retrieve",
                    summary_fields=(
                        StepField("matched_results", "number"),
                    ),
                ),
                PipelineStep(
                    kind="rank",
                    summary_fields=(
                        StepField("ordering", "text"),
                        StepField("tie_break", "text"),
                    ),
                ),
                PipelineStep(
                    kind="shape",
                    summary_fields=(
                        StepField("result_count", "number"),
                        StepField("schema_keys", "json"),
                    ),
                ),
                PipelineStep(
                    kind="report",
                    summary_fields=(
                        StepField("preferred_quality", "text"),
                        StepField("included_warn", "boolean"),
                    ),
                ),
            ),
        ),
    }


def _field(name: str, type_name: str, *, required: bool) -> FunctionParam:
    return FunctionParam(name=name, type_name=type_name, required=required, line=None, column=None)


__all__ = ["pipeline_contracts", "pipeline_definitions", "pipeline_purity"]
