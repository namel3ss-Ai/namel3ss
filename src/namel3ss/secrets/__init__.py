from namel3ss.secrets.audit import record_secret_access, read_secret_audit
from namel3ss.secrets.context import get_audit_root, get_engine_target, set_audit_root, set_engine_target
from namel3ss.secrets.discovery import PROVIDER_ENV, discover_required_secrets, discover_required_secrets_for_profiles
from namel3ss.secrets.model import SecretRef
from namel3ss.secrets.redaction import collect_secret_values, redact_payload, redact_text

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
