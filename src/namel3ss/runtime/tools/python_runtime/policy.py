from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.capabilities.coverage import container_runner_coverage, local_runner_coverage
from namel3ss.runtime.capabilities.gates import check_network, check_secret_allowed, record_capability_check
from namel3ss.runtime.capabilities.gates.base import CapabilityViolation, REASON_COVERAGE_MISSING
from namel3ss.runtime.capabilities.model import CapabilityCheck, CapabilityContext
from namel3ss.runtime.capabilities.secrets import secret_names_in_payload
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.tools.sandbox import sandbox_enabled


def _preflight_capabilities(
    ctx: ExecutionContext,
    capability_ctx: CapabilityContext,
    *,
    runner_name: str,
    payload: object,
    binding,
    resolved_source: str,
    unsafe_override: bool,
    sandbox_override: bool | None = None,
    line: int | None,
    column: int | None,
) -> bool:
    unsafe_used = False
    if runner_name in {"local", "node"}:
        if sandbox_override is not None:
            sandbox_on = sandbox_override
        else:
            sandbox_on = sandbox_enabled(
                resolved_source=resolved_source,
                runner=runner_name,
                binding=binding,
            )
        coverage = local_runner_coverage(capability_ctx.guarantees, sandbox_enabled=sandbox_on)
        if coverage.status != "enforced":
            if unsafe_override:
                unsafe_used = True
            else:
                _record_coverage_block(ctx, capability_ctx, coverage.missing)
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Tool "{capability_ctx.tool_name}" requires sandbox enforcement.',
                        why=f"Sandbox is disabled but guarantees require: {', '.join(coverage.missing)}.",
                        fix="Enable sandbox in tools.yaml or relax the capability overrides.",
                        example='sandbox: true',
                    ),
                    line=line,
                    column=column,
                )
    if runner_name == "container":
        if capability_ctx.guarantees.no_subprocess:
            if unsafe_override:
                unsafe_used = True
            else:
                _record_coverage_block(ctx, capability_ctx, ["subprocess"])
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Tool "{capability_ctx.tool_name}" cannot run in a container runner.',
                        why="Container execution requires subprocess access.",
                        fix="Switch to the local runner or relax the no_subprocess guarantee.",
                        example=f'n3 tools set-runner "{capability_ctx.tool_name}" --runner local',
                    ),
                    line=line,
                    column=column,
                )
        coverage = container_runner_coverage(capability_ctx.guarantees, enforcement=getattr(binding, "enforcement", None))
        if coverage.status == "not_enforceable":
            if unsafe_override:
                unsafe_used = True
            else:
                _record_coverage_block(ctx, capability_ctx, coverage.missing)
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Tool "{capability_ctx.tool_name}" requires container enforcement.',
                        why="Container bindings must declare enforcement coverage.",
                        fix="Set enforcement to declared/verified or choose a local runner.",
                        example='enforcement: "declared"',
                    ),
                    line=line,
                    column=column,
                )
    if runner_name == "service":
        url = binding.url or ctx.config.python_tools.service_url
        if url:
            _gate_capability(
                ctx,
                capability_ctx,
                lambda: check_network(capability_ctx, _record_for(ctx, capability_ctx), url=url, method="POST"),
                line=line,
                column=column,
            )
        _check_payload_secrets(ctx, capability_ctx, payload, line=line, column=column)
    return unsafe_used


def _gate_capability(ctx: ExecutionContext, capability_ctx: CapabilityContext, fn, *, line: int | None, column: int | None) -> None:
    try:
        fn()
    except CapabilityViolation as err:
        raise Namel3ssError(str(err), line=line, column=column) from err


def _check_payload_secrets(
    ctx: ExecutionContext,
    capability_ctx: CapabilityContext,
    payload: object,
    *,
    line: int | None,
    column: int | None,
) -> None:
    if capability_ctx.guarantees.secrets_allowed is None:
        return
    names = secret_names_in_payload(payload, ctx.config)
    if not names:
        return
    record = _record_for(ctx, capability_ctx)
    for name in sorted(names):
        _gate_capability(
            ctx,
            capability_ctx,
            lambda n=name: check_secret_allowed(capability_ctx, record, secret_name=n),
            line=line,
            column=column,
        )


def _record_for(ctx: ExecutionContext, capability_ctx: CapabilityContext):
    return lambda check: record_capability_check(capability_ctx, check, ctx.traces)


def _record_coverage_block(ctx: ExecutionContext, capability_ctx: CapabilityContext, missing: list[str]) -> None:
    for capability in missing:
        source = capability_ctx.guarantees.source_for_capability(capability) or "pack"
        record_capability_check(
            capability_ctx,
            CapabilityCheck(
                capability=capability,
                allowed=False,
                guarantee_source=source,
                reason=REASON_COVERAGE_MISSING,
            ),
            ctx.traces,
        )


__all__ = ["_preflight_capabilities"]
