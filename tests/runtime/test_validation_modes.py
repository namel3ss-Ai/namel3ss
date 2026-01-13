import pytest

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.identity.guards import build_guard_context, enforce_requires
from namel3ss.schema.records import FieldSchema
from namel3ss.schema.identity import IdentitySchema
from namel3ss.validation import ValidationMode


def test_enforce_requires_static_emits_warning() -> None:
    ctx = build_guard_context(identity={}, state={})
    warnings = []
    enforce_requires(
        ctx,
        ir.Literal(value=False, line=1, column=1),
        subject='page "home"',
        line=1,
        column=1,
        mode=ValidationMode.STATIC,
        warnings=warnings,
    )
    assert warnings and warnings[0].code == "requires.skipped"


def test_enforce_requires_runtime_raises() -> None:
    ctx = build_guard_context(identity={}, state={})
    with pytest.raises(Namel3ssError):
        enforce_requires(
            ctx,
            ir.Literal(value=False, line=1, column=1),
            subject='page "home"',
            line=1,
            column=1,
        )


def test_resolve_identity_static_warns_not_raise() -> None:
    schema = IdentitySchema(
        name="user",
        fields=[FieldSchema(name="trust_level", type_name="text", constraint=None)],
        trust_levels=["admin", "user"],
        line=1,
        column=1,
    )
    warnings = []
    identity = resolve_identity(AppConfig(), schema, mode=ValidationMode.STATIC, warnings=warnings)
    assert identity == {}
    assert any(w.code == "identity.missing" for w in warnings)


def test_resolve_identity_runtime_enforces() -> None:
    schema = IdentitySchema(
        name="user",
        fields=[FieldSchema(name="trust_level", type_name="text", constraint=None)],
        trust_levels=["admin", "user"],
        line=1,
        column=1,
    )
    with pytest.raises(Namel3ssError):
        resolve_identity(AppConfig(), schema, mode=ValidationMode.RUNTIME)
