from __future__ import annotations

from pathlib import Path

_BOUNDARY_ATTR = "__namel3ss_boundary__"
_ACTION_ATTR = "__namel3ss_boundary_action__"
_SECRET_ATTR = "__namel3ss_secret_values__"
_ROOT_ATTR = "__namel3ss_project_root__"


def mark_boundary(err: Exception, boundary: str, *, action: str | None = None) -> Exception:
    _set_attr(err, _BOUNDARY_ATTR, boundary, overwrite=False)
    if action:
        _set_attr(err, _ACTION_ATTR, action, overwrite=False)
    return err


def attach_secret_values(err: Exception, secret_values: list[str]) -> None:
    if not secret_values:
        return
    _set_attr(err, _SECRET_ATTR, list(secret_values), overwrite=False)


def attach_project_root(err: Exception, project_root: str | Path | None) -> None:
    if not project_root:
        return
    value = project_root if isinstance(project_root, (str, Path)) else None
    if value is None:
        return
    _set_attr(err, _ROOT_ATTR, str(value), overwrite=False)


def boundary_from_error(err: Exception) -> str | None:
    value = getattr(err, _BOUNDARY_ATTR, None)
    return value if isinstance(value, str) else None


def boundary_action_from_error(err: Exception) -> str | None:
    value = getattr(err, _ACTION_ATTR, None)
    return value if isinstance(value, str) else None


def _set_attr(err: Exception, name: str, value: object, *, overwrite: bool) -> None:
    try:
        if not overwrite and getattr(err, name, None) is not None:
            return
        setattr(err, name, value)
    except Exception:
        return


__all__ = [
    "attach_project_root",
    "attach_secret_values",
    "boundary_action_from_error",
    "boundary_from_error",
    "mark_boundary",
]
