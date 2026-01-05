from __future__ import annotations

from dataclasses import dataclass


STATUS_SHIPPED = "shipped"
STATUS_PARTIAL = "partial"
STATUS_PLANNED = "planned"

CATEGORY_ORDER = (
    "language",
    "compute",
    "tools",
    "ai",
    "memory",
    "reuse",
    "concurrency",
    "runtime",
)

STATUS_ORDER = (STATUS_SHIPPED, STATUS_PARTIAL, STATUS_PLANNED)


@dataclass(frozen=True)
class Capability:
    id: str
    title: str
    category: str
    status: str
    proofs: tuple[str, ...]
    tests: tuple[str, ...]
    examples: tuple[str, ...]


def capabilities() -> list[Capability]:
    return list(_CAPABILITIES)


def _cap(
    *,
    cap_id: str,
    title: str,
    category: str,
    status: str,
    tests: tuple[str, ...],
    examples: tuple[str, ...],
) -> Capability:
    proofs = tests + examples
    return Capability(
        id=cap_id,
        title=title,
        category=category,
        status=status,
        proofs=proofs,
        tests=tests,
        examples=examples,
    )


_CAPABILITIES = (
    _cap(
        cap_id="language.core",
        title="Core declarations and pages",
        category="language",
        status=STATUS_SHIPPED,
        tests=(
            "tests/spec_freeze/test_parser_golden.py",
            "tests/spec_freeze/test_ir_golden.py",
        ),
        examples=(
            "examples/demo_crud_dashboard.ai",
        ),
    ),
    _cap(
        cap_id="compute.core",
        title="Define function and operators",
        category="compute",
        status=STATUS_SHIPPED,
        tests=(
            "tests/runtime/test_functions_runtime.py",
            "tests/runtime/test_runtime_operator_precedence.py",
            "tests/runtime/test_repeat_while_limit.py",
        ),
        examples=(
            "examples/demo_order_totals.ai",
        ),
    ),
    _cap(
        cap_id="compute.collections",
        title="List and map values",
        category="compute",
        status=STATUS_SHIPPED,
        tests=(
            "tests/runtime/test_list_map_operations.py",
        ),
        examples=(
            "examples/demo_order_totals.ai",
        ),
    ),
    _cap(
        cap_id="runtime.tools",
        title="Tool declarations and purity gating",
        category="tools",
        status=STATUS_SHIPPED,
        tests=(
            "tests/runtime/test_tool_e2e.py",
        ),
        examples=(
            "examples/tool_usage/app.ai",
        ),
    ),
    _cap(
        cap_id="runtime.ai",
        title="AI calls and agents",
        category="ai",
        status=STATUS_SHIPPED,
        tests=(
            "tests/runtime/test_ai_execution.py",
            "tests/runtime/test_agents_parallel.py",
        ),
        examples=(
            "examples/demo_multi_agent_orchestration.ai",
        ),
    ),
    _cap(
        cap_id="runtime.memory",
        title="Memory governance and traces",
        category="memory",
        status=STATUS_SHIPPED,
        tests=(
            "tests/traces/test_memory_trace_golden.py",
        ),
        examples=(
            "examples/demo_ai_assistant_over_records.ai",
        ),
    ),
    _cap(
        cap_id="runtime.modules",
        title="Module reuse",
        category="reuse",
        status=STATUS_SHIPPED,
        tests=(
            "tests/modules/test_module_resolver.py",
        ),
        examples=(
            "examples/reuse_modules/app.ai",
        ),
    ),
    _cap(
        cap_id="runtime.memory_packs",
        title="Memory packs and overrides",
        category="memory",
        status=STATUS_SHIPPED,
        tests=(
            "tests/runtime/test_memory_packs.py",
        ),
        examples=(
            "tests/fixtures/memory_packs/app.ai",
        ),
    ),
    _cap(
        cap_id="runtime.concurrency",
        title="Deterministic parallel blocks",
        category="concurrency",
        status=STATUS_SHIPPED,
        tests=(
            "tests/runtime/test_parallel_execution.py",
            "tests/traces/test_parallel_trace_golden.py",
        ),
        examples=(
            "examples/demo_product_dashboard.ai",
        ),
    ),
    _cap(
        cap_id="runtime.traces",
        title="Execution steps and trace events",
        category="runtime",
        status=STATUS_SHIPPED,
        tests=(
            "tests/spec_freeze/test_trace_contracts.py",
        ),
        examples=(
            "examples/control_flow/app.ai",
        ),
    ),
    _cap(
        cap_id="runtime.provider_coverage",
        title="Provider coverage for AI features",
        category="runtime",
        status=STATUS_PARTIAL,
        tests=(
            "tests/providers/test_capabilities.py",
        ),
        examples=(),
    ),
)


__all__ = [
    "Capability",
    "CATEGORY_ORDER",
    "STATUS_PARTIAL",
    "STATUS_PLANNED",
    "STATUS_SHIPPED",
    "STATUS_ORDER",
    "capabilities",
]
