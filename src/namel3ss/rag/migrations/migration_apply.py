from __future__ import annotations

from namel3ss.rag.contracts.value_norms import map_value, text_value
from namel3ss.rag.determinism.json_policy import (
    canonical_contract_copy,
    canonical_contract_hash,
)


def apply_migration_step(state: dict, step: dict[str, object]) -> dict[str, object]:
    operation = text_value(step.get("operation"))
    target_path = text_value(step.get("target_path"))
    from_path = text_value(step.get("from_path"))
    on_missing = text_value(step.get("on_missing"), default="skip") or "skip"
    step_id = text_value(step.get("step_id"))
    step_index = int(step.get("step_index") or 0)
    if not target_path:
        return _step_result(
            step_id=step_id,
            step_index=step_index,
            operation=operation,
            target_path=target_path,
            from_path=from_path,
            status="failed",
            message="missing_target_path",
            before_exists=False,
            after_exists=False,
        )

    target_exists_before, target_before = _read_path(state, target_path)
    if operation == "set_value":
        desired = canonical_contract_copy(step.get("value"))
        if target_exists_before and canonical_contract_hash(target_before) == canonical_contract_hash(desired):
            return _step_result(
                step_id=step_id,
                step_index=step_index,
                operation=operation,
                target_path=target_path,
                from_path=from_path,
                status="skipped",
                message="unchanged",
                before_exists=True,
                after_exists=True,
            )
        _write_path(state, target_path, desired)
        return _step_result(
            step_id=step_id,
            step_index=step_index,
            operation=operation,
            target_path=target_path,
            from_path=from_path,
            status="applied",
            message="value_set",
            before_exists=target_exists_before,
            after_exists=True,
        )

    if operation == "remove_value":
        if not target_exists_before:
            if on_missing == "error":
                status = "failed"
            else:
                status = "skipped"
            return _step_result(
                step_id=step_id,
                step_index=step_index,
                operation=operation,
                target_path=target_path,
                from_path=from_path,
                status=status,
                message="target_missing",
                before_exists=False,
                after_exists=False,
            )
        _delete_path(state, target_path)
        return _step_result(
            step_id=step_id,
            step_index=step_index,
            operation=operation,
            target_path=target_path,
            from_path=from_path,
            status="applied",
            message="value_removed",
            before_exists=True,
            after_exists=False,
        )

    if operation == "rename_value":
        if not from_path:
            return _step_result(
                step_id=step_id,
                step_index=step_index,
                operation=operation,
                target_path=target_path,
                from_path=from_path,
                status="failed",
                message="missing_from_path",
                before_exists=target_exists_before,
                after_exists=target_exists_before,
            )
        source_exists, source_value = _read_path(state, from_path)
        if not source_exists:
            if on_missing == "error":
                status = "failed"
            else:
                status = "skipped"
            return _step_result(
                step_id=step_id,
                step_index=step_index,
                operation=operation,
                target_path=target_path,
                from_path=from_path,
                status=status,
                message="source_missing",
                before_exists=target_exists_before,
                after_exists=target_exists_before,
            )
        if from_path == target_path:
            return _step_result(
                step_id=step_id,
                step_index=step_index,
                operation=operation,
                target_path=target_path,
                from_path=from_path,
                status="skipped",
                message="same_path",
                before_exists=target_exists_before,
                after_exists=target_exists_before,
            )
        _write_path(state, target_path, canonical_contract_copy(source_value))
        _delete_path(state, from_path)
        return _step_result(
            step_id=step_id,
            step_index=step_index,
            operation=operation,
            target_path=target_path,
            from_path=from_path,
            status="applied",
            message="value_renamed",
            before_exists=target_exists_before,
            after_exists=True,
        )

    return _step_result(
        step_id=step_id,
        step_index=step_index,
        operation=operation,
        target_path=target_path,
        from_path=from_path,
        status="failed",
        message="unsupported_operation",
        before_exists=target_exists_before,
        after_exists=target_exists_before,
    )


def already_applied_step_result(step: dict[str, object]) -> dict[str, object]:
    return _step_result(
        step_id=text_value(step.get("step_id")),
        step_index=int(step.get("step_index") or 0),
        operation=text_value(step.get("operation")),
        target_path=text_value(step.get("target_path")),
        from_path=text_value(step.get("from_path")),
        status="skipped",
        message="manifest_already_applied",
        before_exists=False,
        after_exists=False,
    )


def normalize_step_result_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        data = map_value(item)
        rows.append(
            {
                "after_exists": bool(data.get("after_exists")),
                "before_exists": bool(data.get("before_exists")),
                "from_path": text_value(data.get("from_path")),
                "message": text_value(data.get("message")),
                "operation": text_value(data.get("operation")),
                "status": text_value(data.get("status")),
                "step_id": text_value(data.get("step_id")),
                "step_index": int(data.get("step_index") or 0),
                "target_path": text_value(data.get("target_path")),
            }
        )
    rows.sort(key=lambda row: (int(row.get("step_index") or 0), text_value(row.get("step_id"))))
    return rows


def build_step_summary(step_results: list[dict[str, object]]) -> dict[str, int]:
    total_steps = len(step_results)
    applied_steps = sum(1 for row in step_results if text_value(row.get("status")) == "applied")
    failed_steps = sum(1 for row in step_results if text_value(row.get("status")) == "failed")
    skipped_steps = total_steps - applied_steps - failed_steps
    return {
        "applied_steps": applied_steps,
        "failed_steps": failed_steps,
        "skipped_steps": skipped_steps,
        "total_steps": total_steps,
    }


def _step_result(
    *,
    step_id: str,
    step_index: int,
    operation: str,
    target_path: str,
    from_path: str,
    status: str,
    message: str,
    before_exists: bool,
    after_exists: bool,
) -> dict[str, object]:
    return {
        "after_exists": bool(after_exists),
        "before_exists": bool(before_exists),
        "from_path": from_path,
        "message": message,
        "operation": operation,
        "status": status,
        "step_id": step_id,
        "step_index": int(step_index),
        "target_path": target_path,
    }


def _read_path(state: dict, path: str) -> tuple[bool, object]:
    parts = _path_parts(path)
    if not parts:
        return False, None
    node: object = state
    for part in parts:
        if not isinstance(node, dict):
            return False, None
        if part not in node:
            return False, None
        node = node[part]
    return True, canonical_contract_copy(node)


def _write_path(state: dict, path: str, value: object) -> None:
    parts = _path_parts(path)
    if not parts:
        return
    node: dict = state
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = canonical_contract_copy(value)


def _delete_path(state: dict, path: str) -> None:
    parts = _path_parts(path)
    if not parts:
        return
    node: object = state
    for part in parts[:-1]:
        if not isinstance(node, dict):
            return
        node = node.get(part)
    if isinstance(node, dict):
        node.pop(parts[-1], None)


def _path_parts(path: str) -> list[str]:
    token = text_value(path)
    if not token:
        return []
    return [part for part in token.split(".") if part]


__all__ = [
    "already_applied_step_result",
    "apply_migration_step",
    "build_step_summary",
    "normalize_step_result_rows",
]
