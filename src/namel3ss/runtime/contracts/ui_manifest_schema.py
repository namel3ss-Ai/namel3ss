from __future__ import annotations

from namel3ss.runtime.contracts.capability_schema import CAPABILITY_PACK_SCHEMA, CAPABILITY_USAGE_SCHEMA
from namel3ss.runtime.contracts.schema_model import ContractField, ContractSchema


RUNTIME_ERROR_SCHEMA = ContractSchema(
    name="runtime_error",
    notes="Canonical user-safe runtime error payload.",
    additional_fields=False,
    fields=(
        ContractField(
            "category",
            "string",
            notes="Closed-set runtime error category.",
        ),
        ContractField("message", "string", notes="User-safe summary."),
        ContractField("hint", "string", notes="Actionable remediation."),
        ContractField("origin", "string", notes="Subsystem origin."),
        ContractField("stable_code", "string", notes="Deterministic stable code."),
    ),
)

CONTRACT_WARNING_SCHEMA = ContractSchema(
    name="contract_warning",
    notes="Non-blocking contract validation warning emitted in dev/studio.",
    additional_fields=False,
    fields=(
        ContractField("code", "string"),
        ContractField("message", "string"),
        ContractField("path", "string"),
        ContractField("expected", "string", required=False, default=None),
        ContractField("actual", "string", required=False, default=None),
    ),
)

RETRIEVAL_TRACE_ENTRY_SCHEMA = ContractSchema(
    name="retrieval_trace_entry",
    notes="Deterministic retrieval evidence row used for citations and explainability.",
    additional_fields=True,
    fields=(
        ContractField("chunk_id", "string"),
        ContractField("document_id", "string"),
        ContractField("page_number", "number"),
        ContractField("score", "number"),
        ContractField("rank", "number"),
        ContractField("reason", "string"),
    ),
)

RETRIEVAL_PLAN_SCHEMA = ContractSchema(
    name="retrieval_plan",
    notes="Serializable retrieval plan with filters, cutoffs, and deterministic ordering metadata.",
    additional_fields=True,
    fields=(
        ContractField("query", "string"),
        ContractField("scope", "object", required=False, default=None),
        ContractField("tier", "object", required=False, default=None),
        ContractField("filters", "array", required=False, item_type="object", default=()),
        ContractField("cutoffs", "object", required=False, default=None),
        ContractField("ordering", "string", required=False, default=None),
        ContractField("selected_chunk_ids", "array", required=False, item_type="string", default=()),
    ),
)

TRUST_SCORE_DETAILS_SCHEMA = ContractSchema(
    name="trust_score_details",
    notes="Deterministic trust score metadata derived from retrieval evidence.",
    additional_fields=True,
    fields=(
        ContractField("formula_version", "string"),
        ContractField("score", "number"),
        ContractField("level", "string"),
        ContractField("inputs", "object", required=False, default=None),
        ContractField("components", "array", required=False, item_type="object", default=()),
        ContractField("penalties", "array", required=False, item_type="object", default=()),
    ),
)

PERSISTENCE_BACKEND_SCHEMA = ContractSchema(
    name="persistence_backend",
    notes="Configured persistence backend descriptor.",
    additional_fields=True,
    fields=(
        ContractField("target", "string"),
        ContractField("kind", "string"),
        ContractField("enabled", "boolean"),
        ContractField("durable", "boolean"),
        ContractField("deterministic_ordering", "boolean"),
        ContractField("descriptor", "string", required=False, default=None),
        ContractField("requires_network", "boolean", required=False, default=False),
        ContractField("replicas", "array", required=False, item_type="string", default=()),
    ),
)

MIGRATION_STATUS_SCHEMA = ContractSchema(
    name="migration_status",
    notes="Deterministic migration status for runtime startup and inspection.",
    additional_fields=True,
    fields=(
        ContractField("schema_version", "string"),
        ContractField("state_schema_version", "string"),
        ContractField("plan_id", "string"),
        ContractField("last_plan_id", "string"),
        ContractField("applied_plan_id", "string"),
        ContractField("pending", "boolean"),
        ContractField("breaking", "boolean"),
        ContractField("reversible", "boolean"),
        ContractField("plan_changed", "boolean"),
        ContractField("change_count", "number"),
        ContractField("error", "string", required=False, default=None),
    ),
)

AUDIT_POLICY_STATUS_SCHEMA = ContractSchema(
    name="audit_policy_status",
    notes="Resolved audit mode and write outcome for the current response.",
    additional_fields=True,
    fields=(
        ContractField("mode", "string"),
        ContractField("required", "boolean"),
        ContractField("forbidden", "boolean"),
        ContractField("attempted", "boolean"),
        ContractField("written", "boolean"),
        ContractField("error", "string", required=False, default=None),
    ),
)

AUDIT_BUNDLE_SCHEMA = ContractSchema(
    name="audit_bundle",
    notes="Immutable audit bundle metadata under .namel3ss/audit.",
    additional_fields=True,
    fields=(
        ContractField("schema_version", "string"),
        ContractField("run_id", "string"),
        ContractField("integrity_hash", "string"),
        ContractField("run_artifact_path", "string"),
        ContractField("bundle_path", "string"),
    ),
)

RUN_DIFF_CHANGE_SCHEMA = ContractSchema(
    name="run_diff_change",
    notes="Deterministic field-level diff entry for Studio run comparison.",
    additional_fields=False,
    fields=(
        ContractField("field", "string"),
        ContractField("changed", "boolean"),
        ContractField("left_hash", "string"),
        ContractField("right_hash", "string"),
    ),
)

RUN_DIFF_SCHEMA = ContractSchema(
    name="run_diff",
    notes="Deterministic run diff comparing the latest two run artifacts.",
    additional_fields=False,
    fields=(
        ContractField("schema_version", "string"),
        ContractField("left_run_id", "string", required=False, default=None),
        ContractField("right_run_id", "string", required=False, default=None),
        ContractField("changed", "boolean"),
        ContractField("change_count", "number"),
        ContractField("changes", "array", required=False, item_ref="run_diff_change", default=()),
    ),
)

REPRO_BUNDLE_SCHEMA = ContractSchema(
    name="repro_bundle",
    notes="Minimal deterministic repro payload for Studio sharing.",
    additional_fields=True,
    fields=(
        ContractField("schema_version", "string"),
        ContractField("workspace_id", "string"),
        ContractField("session_id", "string"),
        ContractField("run_id", "string"),
        ContractField("repro_path", "string", required=False, default=None),
        ContractField("app_hash", "string", required=False, default=None),
        ContractField("program_entrypoint", "string", required=False, default=None),
        ContractField("input_snapshot", "object", required=False, default=None),
        ContractField("prompt", "object", required=False, default=None),
        ContractField("output", "any", required=False, default=None),
        ContractField("retrieval_trace", "array", required=False, item_ref="retrieval_trace_entry", default=()),
        ContractField("trust_score_details", "object", required=False, ref="trust_score_details"),
        ContractField("runtime_errors", "array", required=False, item_ref="runtime_error", default=()),
    ),
)

RUN_ARTIFACT_SCHEMA = ContractSchema(
    name="run_artifact",
    notes="Deterministic replay artifact for a runtime flow/action execution.",
    additional_fields=True,
    fields=(
        ContractField("schema_version", "string"),
        ContractField("run_id", "string"),
        ContractField("program", "object", required=False, default=None),
        ContractField("inputs", "object", required=False, default=None),
        ContractField("ingestion_artifacts", "object", required=False, default=None),
        ContractField("retrieval_plan", "object", required=False, ref="retrieval_plan"),
        ContractField("retrieval_trace", "array", required=False, item_ref="retrieval_trace_entry", default=()),
        ContractField("trust_score_details", "object", required=False, ref="trust_score_details"),
        ContractField("prompt", "object", required=False, default=None),
        ContractField("model_config", "object", required=False, default=None),
        ContractField("capabilities_enabled", "array", required=False, item_ref="capability_pack", default=()),
        ContractField("capability_versions", "object", required=False, default=None),
        ContractField("capability_usage", "array", required=False, item_ref="capability_usage", default=()),
        ContractField("output", "any", required=False, default=None),
        ContractField("runtime_errors", "array", required=False, item_ref="runtime_error", default=()),
        ContractField("checksums", "object", required=False, default=None),
    ),
)

RETRIEVAL_STATE_SCHEMA = ContractSchema(
    name="retrieval_state",
    notes="Structured retrieval state shared by headless and Studio clients.",
    additional_fields=True,
    fields=(
        ContractField("retrieval_plan", "object", required=False, ref="retrieval_plan"),
        ContractField("retrieval_trace", "array", required=False, item_ref="retrieval_trace_entry", default=()),
        ContractField("trust_score_details", "object", required=False, ref="trust_score_details"),
    ),
)

RAG_STATE_SCHEMA = ContractSchema(
    name="rag_state",
    notes="RAG-focused state subset used by upload, ingestion, and retrieval clients.",
    additional_fields=True,
    fields=(
        ContractField("uploads", "object", required=False, default=None),
        ContractField("ingestion", "object", required=False, default=None),
        ContractField("retrieval", "object", required=False, ref="retrieval_state"),
        ContractField("chat", "object", required=False, default=None),
    ),
)

UI_STATE_SCHEMA = ContractSchema(
    name="ui_state",
    notes="State envelope used by /api/ui/state and optional headless state inclusion.",
    additional_fields=False,
    fields=(
        ContractField("current_page", "string", required=False, default=None),
        ContractField("values", "object", required=True, ref="rag_state"),
        ContractField("errors", "array", required=True, item_type="object", default=()),
    ),
)

MANIFEST_PAGE_SCHEMA = ContractSchema(
    name="manifest_page",
    notes="Minimal page shape for deterministic UI manifests.",
    additional_fields=True,
    fields=(
        ContractField("name", "string", required=False, default=None),
        ContractField("slug", "string", required=False, default=None),
        ContractField("elements", "array", required=False, item_type="object", default=()),
        ContractField("layout", "object", required=False, default=None),
    ),
)

UI_MANIFEST_SCHEMA = ContractSchema(
    name="ui_manifest",
    notes="Canonical UI manifest payload shape consumed by headless and browser clients.",
    additional_fields=True,
    fields=(
        ContractField("ok", "boolean", required=False, default=True),
        ContractField("pages", "array", item_ref="manifest_page", default=()),
        ContractField("actions", "object", required=False, default=None),
        ContractField("upload_requests", "array", required=False, item_type="object", default=()),
        ContractField("warnings", "array", required=False, item_type="object", default=()),
        ContractField("mode", "string", required=False, default=None),
        ContractField("theme", "object", required=False, default=None),
        ContractField("runtime_error", "object", required=False, ref="runtime_error"),
        ContractField("runtime_errors", "array", required=False, item_ref="runtime_error", default=()),
        ContractField("capabilities_enabled", "array", required=False, item_ref="capability_pack", default=()),
        ContractField("capability_versions", "object", required=False, default=None),
        ContractField("persistence_backend", "object", required=False, ref="persistence_backend"),
        ContractField("state_schema_version", "string", required=False, default=None),
        ContractField("migration_status", "object", required=False, ref="migration_status"),
        ContractField("run_artifact", "object", required=False, ref="run_artifact"),
        ContractField("audit_bundle", "object", required=False, ref="audit_bundle"),
        ContractField("audit_policy_status", "object", required=False, ref="audit_policy_status"),
        ContractField("workspace_id", "string", required=False, default=None),
        ContractField("session_id", "string", required=False, default=None),
        ContractField("run_diff", "object", required=False, ref="run_diff"),
        ContractField("repro_bundle", "object", required=False, ref="repro_bundle"),
        ContractField("run_history", "array", required=False, item_type="string", default=()),
    ),
)


__all__ = [
    "AUDIT_BUNDLE_SCHEMA",
    "AUDIT_POLICY_STATUS_SCHEMA",
    "CAPABILITY_PACK_SCHEMA",
    "CAPABILITY_USAGE_SCHEMA",
    "CONTRACT_WARNING_SCHEMA",
    "MANIFEST_PAGE_SCHEMA",
    "MIGRATION_STATUS_SCHEMA",
    "PERSISTENCE_BACKEND_SCHEMA",
    "RAG_STATE_SCHEMA",
    "REPRO_BUNDLE_SCHEMA",
    "RETRIEVAL_PLAN_SCHEMA",
    "RETRIEVAL_STATE_SCHEMA",
    "RETRIEVAL_TRACE_ENTRY_SCHEMA",
    "RUN_DIFF_CHANGE_SCHEMA",
    "RUN_DIFF_SCHEMA",
    "RUN_ARTIFACT_SCHEMA",
    "RUNTIME_ERROR_SCHEMA",
    "TRUST_SCORE_DETAILS_SCHEMA",
    "UI_MANIFEST_SCHEMA",
    "UI_STATE_SCHEMA",
]
