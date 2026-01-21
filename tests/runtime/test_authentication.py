from __future__ import annotations

import json

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.auth.auth_context import resolve_auth_context
from namel3ss.runtime.auth.auth_routes import handle_login, handle_logout, handle_session
from namel3ss.runtime.auth.identity_model import build_identity_summary, normalize_identity
from namel3ss.runtime.auth.permission_helpers import has_permission, has_role
from namel3ss.runtime.auth.session_store import SessionStore
from namel3ss.runtime.auth.token_codec import issue_token
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.runtime.store.memory_store import MemoryStore


def test_identity_helpers_are_deterministic() -> None:
    identity = {
        "id": "user-1",
        "roles": {"editor", "admin"},
        "permissions": ["read", "read", "write"],
        "trust_level": "member",
    }
    normalized = normalize_identity(identity)
    assert normalized["subject"] == "user-1"
    assert normalized["roles"] == ["admin", "editor"]
    assert normalized["role"] == "admin"
    assert normalized["permissions"] == ["read", "write"]
    assert has_role(identity, "admin") is True
    assert has_permission(identity, "write") is True

    summary = build_identity_summary(identity)
    assert summary == {
        "subject": "user-1",
        "roles": ["admin", "editor"],
        "permissions": ["read", "write"],
        "trust_level": "member",
    }

    scopes = normalize_identity({"scopes": "alpha, beta"})
    assert scopes["permissions"] == ["alpha", "beta"]


def test_session_store_persists_and_is_deterministic(tmp_path) -> None:
    config = AppConfig()
    config.persistence.target = "sqlite"
    config.persistence.db_path = str(tmp_path / "auth.db")
    store = resolve_store(None, config=config)
    session_store = SessionStore(store)
    session = session_store.create_session({"subject": "user-1", "roles": ["admin"]}, expires_in=3)
    assert session.session_id == "session_1"
    assert session.created_tick == 1
    assert session.expires_at == 4
    summary = session_store.session_summary(session)
    assert summary["id"].startswith("session:")
    assert summary["id"] != session.session_id

    store_again = resolve_store(None, config=config)
    session_store_again = SessionStore(store_again)
    fetched = session_store_again.get_session(session.session_id)
    assert fetched is not None
    assert fetched.status == "active"

    assert session_store_again.revoke_session(session.session_id) is True
    store_third = resolve_store(None, config=config)
    session_store_third = SessionStore(store_third)
    revoked = session_store_third.get_session(session.session_id)
    assert revoked is not None
    assert revoked.status == "revoked"


def test_token_status_categories_are_stable() -> None:
    config = AppConfig()
    config.authentication.signing_key = "signing-key"

    token_valid = issue_token({"subject": "user-1"}, session_id=None, signing_key="signing-key", expires_at=5)
    ctx_valid = resolve_auth_context(
        {"Authorization": f"Bearer {token_valid}"},
        config=config,
        identity_schema=None,
        store=MemoryStore(),
    )
    assert ctx_valid.token_status == "valid"
    assert ctx_valid.authenticated is True

    token_expired = issue_token({"subject": "user-1"}, session_id=None, signing_key="signing-key", expires_at=0)
    ctx_expired = resolve_auth_context(
        {"Authorization": f"Bearer {token_expired}"},
        config=config,
        identity_schema=None,
        store=MemoryStore(),
    )
    assert ctx_expired.token_status == "expired"
    assert ctx_expired.error == "token_expired"

    token_invalid = issue_token({"subject": "user-1"}, session_id=None, signing_key="other-key", expires_at=5)
    ctx_invalid = resolve_auth_context(
        {"Authorization": f"Bearer {token_invalid}"},
        config=config,
        identity_schema=None,
        store=MemoryStore(),
    )
    assert ctx_invalid.token_status == "revoked"
    assert ctx_invalid.error == "token_invalid"


def test_auth_routes_return_redacted_payloads() -> None:
    config = AppConfig()
    config.authentication.allow_identity = True
    config.authentication.signing_key = "signing-key"
    store = MemoryStore()
    body = {
        "identity": {
            "subject": "demo-user",
            "roles": ["admin"],
            "permissions": ["reports.view"],
            "trust_level": "member",
        },
        "issue_token": True,
    }
    payload, status, headers = handle_login({}, body, config=config, identity_schema=None, store=store)
    assert status == 200
    cookie = headers.get("Set-Cookie") or ""
    raw_session = cookie.split(";", 1)[0].split("=", 1)[-1]
    assert payload["session"]["id"].startswith("session:")
    assert payload["session"]["id"] != raw_session
    token = payload["token"]["token"]
    assert payload["token"]["fingerprint"].startswith("token:")
    assert token not in json.dumps(payload.get("traces", []))

    session_payload, session_status, _ = handle_session(
        {"Cookie": f"n3_session={raw_session}"},
        config=config,
        identity_schema=None,
        store=store,
    )
    assert session_status == 200
    assert session_payload["auth"]["authenticated"] is True
    assert session_payload["session"]["id"].startswith("session:")

    token_payload, token_status, _ = handle_session(
        {"Authorization": f"Bearer {token}"},
        config=config,
        identity_schema=None,
        store=store,
    )
    assert token_status == 200
    assert token_payload["auth"]["token"].startswith("token:")
    assert token not in json.dumps(token_payload)

    logout_payload, logout_status, logout_headers = handle_logout(
        {"Cookie": f"n3_session={raw_session}"},
        config=config,
        identity_schema=None,
        store=store,
    )
    assert logout_status == 200
    assert logout_payload["session"]["id"].startswith("session:")
    assert logout_headers.get("Set-Cookie", "").startswith("n3_session=")


def test_requires_guidance_for_missing_authentication() -> None:
    source = '''spec is "1.0"

identity "user":
  field "role" is text

flow "secure": requires has_role("admin")
  return "ok"
'''
    program = lower_program(parse(source))
    flow = next(flow for flow in program.flows if flow.name == "secure")
    schemas = {schema.name: schema for schema in program.records}
    config = AppConfig()
    store = MemoryStore()
    auth_ctx = resolve_auth_context({}, config=config, identity_schema=getattr(program, "identity", None), store=store)
    executor = Executor(
        flow,
        schemas=schemas,
        initial_state={},
        store=store,
        functions=program.functions,
        runtime_theme=getattr(program, "theme", None),
        identity_schema=getattr(program, "identity", None),
        identity=auth_ctx.identity,
        auth_context=auth_ctx,
        pack_allowlist=getattr(program, "pack_allowlist", None),
        config=config,
    )
    with pytest.raises(Namel3ssError) as err:
        executor.run()
    message = str(err.value)
    assert "requires authentication" in message
    assert err.value.details.get("category") == "authentication"
    assert err.value.details.get("reason_code") == "missing_authentication"
