from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_persistence_root, resolve_project_root
from namel3ss.utils.simple_yaml import parse_yaml, render_yaml


TENANTS_FILENAME = "tenants.yaml"
CURRENT_TENANT_FILENAME = "current_tenant"


@dataclass(frozen=True)
class TenantSpec:
    tenant_id: str
    name: str
    namespace_prefix: str
    storage_backend: str
    resource_quotas: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        quotas = {key: float(self.resource_quotas[key]) for key in sorted(self.resource_quotas.keys())}
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "namespace_prefix": self.namespace_prefix,
            "storage_backend": self.storage_backend,
            "resource_quotas": quotas,
        }


@dataclass(frozen=True)
class TenantRegistry:
    tenants: tuple[TenantSpec, ...]

    def sorted_tenants(self) -> tuple[TenantSpec, ...]:
        return tuple(sorted(self.tenants, key=lambda item: item.tenant_id))

    def find(self, tenant_id: str) -> TenantSpec | None:
        normalized = _normalize_tenant_id(tenant_id)
        for tenant in self.tenants:
            if tenant.tenant_id == normalized:
                return tenant
        return None

    def default(self) -> TenantSpec | None:
        ordered = self.sorted_tenants()
        return ordered[0] if ordered else None


def tenants_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_project_root(project_root, app_path)
    if root is None:
        return None
    return Path(root) / TENANTS_FILENAME


def current_tenant_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    root = resolve_persistence_root(project_root, app_path)
    if root is None:
        return None
    return Path(root) / ".namel3ss" / CURRENT_TENANT_FILENAME


def load_tenant_registry(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    required: bool = False,
) -> TenantRegistry:
    path = tenants_path(project_root, app_path)
    if path is None:
        if required:
            raise Namel3ssError(_missing_registry_message("tenants.yaml"))
        return TenantRegistry(tenants=())
    if not path.exists():
        if required:
            raise Namel3ssError(_missing_registry_message(path.as_posix()))
        return TenantRegistry(tenants=())
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_registry_message(path, str(err))) from err
    tenants = _parse_tenant_rows(payload, path=path)
    return TenantRegistry(tenants=tuple(sorted(tenants, key=lambda item: item.tenant_id)))


def save_tenant_registry(
    project_root: str | Path | None,
    app_path: str | Path | None,
    registry: TenantRegistry,
) -> Path:
    path = tenants_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Tenant config path could not be resolved.")
    payload = {"tenants": [tenant.to_dict() for tenant in registry.sorted_tenants()]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_yaml(payload), encoding="utf-8")
    return path


def add_tenant(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    tenant_id: str,
    name: str,
    namespace_prefix: str,
    storage_backend: str,
    resource_quotas: dict[str, float] | None = None,
) -> tuple[Path, TenantSpec]:
    entry = TenantSpec(
        tenant_id=_normalize_tenant_id(tenant_id),
        name=_require_text(name, "name"),
        namespace_prefix=_require_text(namespace_prefix, "namespace_prefix"),
        storage_backend=_require_text(storage_backend, "storage_backend"),
        resource_quotas=_normalize_quotas(resource_quotas),
    )
    if not entry.tenant_id:
        raise Namel3ssError(_invalid_tenant_id_message())
    registry = load_tenant_registry(project_root, app_path)
    if registry.find(entry.tenant_id):
        raise Namel3ssError(_duplicate_tenant_message(entry.tenant_id))
    updated = list(registry.tenants)
    updated.append(entry)
    path = save_tenant_registry(project_root, app_path, TenantRegistry(tenants=tuple(updated)))
    return path, entry


def list_tenants(project_root: str | Path | None, app_path: str | Path | None) -> list[dict[str, object]]:
    registry = load_tenant_registry(project_root, app_path)
    current = get_current_tenant(project_root, app_path)
    rows: list[dict[str, object]] = []
    for tenant in registry.sorted_tenants():
        row = tenant.to_dict()
        row["is_current"] = tenant.tenant_id == current
        rows.append(row)
    return rows


def set_current_tenant(
    project_root: str | Path | None,
    app_path: str | Path | None,
    tenant_id: str,
) -> Path:
    normalized = _normalize_tenant_id(tenant_id)
    if not normalized:
        raise Namel3ssError(_invalid_tenant_id_message())
    registry = load_tenant_registry(project_root, app_path, required=True)
    if registry.find(normalized) is None:
        raise Namel3ssError(_unknown_tenant_message(normalized))
    path = current_tenant_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Current tenant path could not be resolved.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(normalized + "\n", encoding="utf-8")
    return path


def get_current_tenant(project_root: str | Path | None, app_path: str | Path | None) -> str | None:
    path = current_tenant_path(project_root, app_path)
    if path is None or not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    normalized = _normalize_tenant_id(text)
    return normalized or None


def resolve_request_tenant(
    *,
    headers: dict[str, str] | None,
    query_values: dict[str, str] | None,
    identity: dict | None,
    project_root: str | Path | None,
    app_path: str | Path | None,
) -> str | None:
    registry = load_tenant_registry(project_root, app_path)
    requested = _requested_tenant(headers=headers, query_values=query_values)
    identity_tenants = _identity_tenants(identity)
    current = get_current_tenant(project_root, app_path)
    if not registry.tenants:
        if requested:
            raise Namel3ssError(
                _unknown_tenant_message(requested),
                details={"http_status": 403, "category": "permission", "reason_code": "tenant_missing"},
            )
        return identity_tenants[0] if identity_tenants else None
    fallback = registry.default().tenant_id if registry.default() else None
    active = requested or (identity_tenants[0] if identity_tenants else None) or current or fallback
    if not active:
        return None
    tenant = registry.find(active)
    if tenant is None:
        raise Namel3ssError(
            _unknown_tenant_message(active),
            details={"http_status": 403, "category": "permission", "reason_code": "tenant_missing"},
        )
    if identity_tenants and active not in identity_tenants:
        raise Namel3ssError(
            _tenant_access_denied_message(active),
            details={"http_status": 403, "category": "permission", "reason_code": "tenant_access_denied"},
        )
    return tenant.tenant_id


def tenant_storage_root(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    tenant_id: str,
    allow_create: bool = True,
) -> Path | None:
    root = resolve_persistence_root(project_root, app_path, allow_create=allow_create)
    if root is None:
        return None
    tenant = _normalize_tenant_id(tenant_id)
    if not tenant:
        raise Namel3ssError(_invalid_tenant_id_message())
    path = Path(root) / ".namel3ss" / f"tenant_{tenant}"
    if allow_create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def enforce_quota(tenant: TenantSpec, *, metric: str, used: float) -> None:
    key = str(metric or "").strip()
    if not key:
        return
    limit = tenant.resource_quotas.get(key)
    if limit is None:
        return
    if float(used) <= float(limit):
        return
    raise Namel3ssError(
        _quota_exceeded_message(tenant.tenant_id, key, used=float(used), limit=float(limit)),
        details={"http_status": 429, "category": "quota", "reason_code": "tenant_quota_exceeded"},
    )


def _parse_tenant_rows(payload: object, *, path: Path) -> list[TenantSpec]:
    if isinstance(payload, dict):
        values = payload.get("tenants", payload)
    else:
        values = payload
    rows: list[dict[str, object]] = []
    if isinstance(values, list):
        for row in values:
            if not isinstance(row, dict):
                raise Namel3ssError(_invalid_registry_message(path, "tenant entry must be an object"))
            rows.append(row)
    elif isinstance(values, dict):
        for tenant_id in sorted(values.keys(), key=lambda item: str(item)):
            raw = values.get(tenant_id)
            if not isinstance(raw, dict):
                raise Namel3ssError(_invalid_registry_message(path, f"tenant '{tenant_id}' must be an object"))
            row = dict(raw)
            row.setdefault("tenant_id", str(tenant_id))
            rows.append(row)
    else:
        raise Namel3ssError(_invalid_registry_message(path, "tenants must be a list or map"))
    specs: list[TenantSpec] = []
    seen: set[str] = set()
    for row in rows:
        tenant_id = _normalize_tenant_id(row.get("tenant_id"))
        if not tenant_id:
            raise Namel3ssError(_invalid_tenant_id_message())
        if tenant_id in seen:
            raise Namel3ssError(_duplicate_tenant_message(tenant_id))
        seen.add(tenant_id)
        specs.append(
            TenantSpec(
                tenant_id=tenant_id,
                name=_require_text(row.get("name"), "name"),
                namespace_prefix=_require_text(row.get("namespace_prefix"), "namespace_prefix"),
                storage_backend=_require_text(row.get("storage_backend"), "storage_backend"),
                resource_quotas=_normalize_quotas(row.get("resource_quotas")),
            )
        )
    return specs


def _normalize_quotas(value: object) -> dict[str, float]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise Namel3ssError(_invalid_quota_message("resource_quotas must be a map"))
    quotas: dict[str, float] = {}
    for key in sorted(value.keys(), key=lambda item: str(item)):
        name = str(key or "").strip()
        if not name:
            continue
        raw = value.get(key)
        if isinstance(raw, bool) or raw is None:
            raise Namel3ssError(_invalid_quota_message(f"quota '{name}' must be a non-negative number"))
        try:
            parsed = float(raw)
        except Exception as err:
            raise Namel3ssError(_invalid_quota_message(f"quota '{name}' must be a non-negative number")) from err
        if parsed < 0:
            raise Namel3ssError(_invalid_quota_message(f"quota '{name}' must be a non-negative number"))
        quotas[name] = parsed
    return quotas


def _identity_tenants(identity: dict | None) -> tuple[str, ...]:
    if not isinstance(identity, dict):
        return ()
    values: list[str] = []
    for key in ("tenant", "tenant_id"):
        raw = identity.get(key)
        normalized = _normalize_tenant_id(raw)
        if normalized and normalized not in values:
            values.append(normalized)
    raw_tenants = identity.get("tenants")
    if isinstance(raw_tenants, list):
        for item in raw_tenants:
            normalized = _normalize_tenant_id(item)
            if normalized and normalized not in values:
                values.append(normalized)
    return tuple(values)


def _requested_tenant(*, headers: dict[str, str] | None, query_values: dict[str, str] | None) -> str | None:
    query = query_values or {}
    for key in ("tenant", "tenant_id"):
        value = _normalize_tenant_id(query.get(key))
        if value:
            return value
    if not headers:
        return None
    for name, value in headers.items():
        lowered = name.lower()
        if lowered in {"x-n3-tenant", "x-tenant-id", "tenant"}:
            normalized = _normalize_tenant_id(value)
            if normalized:
                return normalized
    return None


def _normalize_tenant_id(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    cleaned: list[str] = []
    for char in text:
        if char.isalnum() or char in {"_", "-"}:
            cleaned.append(char)
        else:
            cleaned.append("_")
    normalized = "".join(cleaned).strip("_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized


def _require_text(value: object, label: str) -> str:
    text = str(value or "").strip()
    if text:
        return text
    raise Namel3ssError(_missing_field_message(label))


def _missing_registry_message(path: str) -> str:
    return build_guidance_message(
        what="Tenant config is missing.",
        why=f"Expected {path}.",
        fix="Create tenants.yaml before using tenant commands.",
        example="tenants:\n  - tenant_id: acme\n    name: ACME Corp\n    namespace_prefix: acme_\n    storage_backend: local",
    )


def _invalid_registry_message(path: Path, detail: str) -> str:
    return build_guidance_message(
        what="Tenant config is invalid.",
        why=f"{path.as_posix()} could not be parsed: {detail}.",
        fix="Correct tenants.yaml and retry.",
        example="tenants:\n  - tenant_id: acme\n    name: ACME Corp\n    namespace_prefix: acme_\n    storage_backend: local",
    )


def _invalid_tenant_id_message() -> str:
    return build_guidance_message(
        what="tenant_id is invalid.",
        why="tenant_id cannot be empty.",
        fix="Use letters, numbers, dash, or underscore.",
        example="acme",
    )


def _duplicate_tenant_message(tenant_id: str) -> str:
    return build_guidance_message(
        what=f"Tenant '{tenant_id}' already exists.",
        why="tenant_id must be unique.",
        fix="Use another tenant_id or update the existing entry.",
        example="n3 tenant add acme_team \"ACME Team\" acme_team_ local",
    )


def _unknown_tenant_message(tenant_id: str) -> str:
    return build_guidance_message(
        what=f"Tenant '{tenant_id}' was not found.",
        why="The tenant is not defined in tenants.yaml.",
        fix="Add the tenant or pick a valid tenant id.",
        example="n3 tenant list",
    )


def _tenant_access_denied_message(tenant_id: str) -> str:
    return build_guidance_message(
        what=f"Access denied for tenant '{tenant_id}'.",
        why="The authenticated identity does not include this tenant.",
        fix="Use a token for the target tenant or change the requested tenant.",
        example="X-N3-Tenant: acme",
    )


def _invalid_quota_message(detail: str) -> str:
    return build_guidance_message(
        what="Tenant quota config is invalid.",
        why=detail,
        fix="Set resource_quotas as key:number pairs.",
        example="resource_quotas:\n  max_flows: 100\n  memory_gb: 8",
    )


def _quota_exceeded_message(tenant_id: str, metric: str, *, used: float, limit: float) -> str:
    return build_guidance_message(
        what=f"Tenant '{tenant_id}' exceeded quota '{metric}'.",
        why=f"Used {used} but limit is {limit}.",
        fix="Lower usage or raise tenant quotas.",
        example="resource_quotas:\n  max_flows: 200",
    )


def _missing_field_message(label: str) -> str:
    return build_guidance_message(
        what=f"{label} is required.",
        why=f"Tenant entries must include '{label}'.",
        fix=f"Set '{label}' in tenants.yaml.",
        example="tenant_id: acme",
    )


__all__ = [
    "CURRENT_TENANT_FILENAME",
    "TENANTS_FILENAME",
    "TenantRegistry",
    "TenantSpec",
    "add_tenant",
    "current_tenant_path",
    "enforce_quota",
    "get_current_tenant",
    "list_tenants",
    "load_tenant_registry",
    "resolve_request_tenant",
    "save_tenant_registry",
    "set_current_tenant",
    "tenant_storage_root",
    "tenants_path",
]
