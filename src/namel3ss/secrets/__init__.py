__all__ = [
    "PROVIDER_ENV",
    "SecretRef",
    "collect_secret_values",
    "discover_required_secrets",
    "discover_required_secrets_for_profiles",
    "get_audit_root",
    "get_engine_target",
    "record_secret_access",
    "read_secret_audit",
    "redact_payload",
    "redact_text",
    "set_audit_root",
    "set_engine_target",
]


def __getattr__(name: str):
    if name in {"record_secret_access", "read_secret_audit"}:
        from namel3ss.secrets.audit import record_secret_access, read_secret_audit

        return {"record_secret_access": record_secret_access, "read_secret_audit": read_secret_audit}[name]
    if name in {"get_audit_root", "get_engine_target", "set_audit_root", "set_engine_target"}:
        from namel3ss.secrets.context import (
            get_audit_root,
            get_engine_target,
            set_audit_root,
            set_engine_target,
        )

        return {
            "get_audit_root": get_audit_root,
            "get_engine_target": get_engine_target,
            "set_audit_root": set_audit_root,
            "set_engine_target": set_engine_target,
        }[name]
    if name in {"PROVIDER_ENV", "discover_required_secrets", "discover_required_secrets_for_profiles"}:
        from namel3ss.secrets.discovery import (
            PROVIDER_ENV,
            discover_required_secrets,
            discover_required_secrets_for_profiles,
        )

        return {
            "PROVIDER_ENV": PROVIDER_ENV,
            "discover_required_secrets": discover_required_secrets,
            "discover_required_secrets_for_profiles": discover_required_secrets_for_profiles,
        }[name]
    if name == "SecretRef":
        from namel3ss.secrets.model import SecretRef

        return SecretRef
    if name in {"collect_secret_values", "redact_payload", "redact_text"}:
        from namel3ss.secrets.redaction import collect_secret_values, redact_payload, redact_text

        return {
            "collect_secret_values": collect_secret_values,
            "redact_payload": redact_payload,
            "redact_text": redact_text,
        }[name]
    raise AttributeError(f"module 'namel3ss.secrets' has no attribute {name!r}")
