from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.governance.rbac import add_user, generate_token
from namel3ss.governance.secrets import add_secret
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.auth.auth_context import resolve_auth_context
from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.secrets_store import resolve_secret_value
from namel3ss.runtime.store.memory_store import MemoryStore


SOURCE = 'spec is "1.0"\n\nflow "demo_flow":\n  return "ok"\n'


def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text(SOURCE, encoding="utf-8")
    return app


def _build_program(app_path: Path):
    program = lower_program(parse(SOURCE))
    program.project_root = app_path.parent.as_posix()
    program.app_path = app_path.as_posix()
    return program


def test_static_token_auth_context_and_flow_permission_enforcement(tmp_path: Path, monkeypatch) -> None:
    app_path = _write_app(tmp_path)
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", home.as_posix())

    add_user(project_root=tmp_path, app_path=app_path, username="alice", roles=["developer"])
    token = generate_token("alice")

    auth = resolve_auth_context(
        {"Authorization": f"Bearer {token}"},
        config=AppConfig(),
        identity_schema=None,
        store=MemoryStore(),
        project_root=tmp_path.as_posix(),
        app_path=app_path.as_posix(),
    )
    assert auth.authenticated is True
    assert auth.token_status == "static"
    assert auth.identity.get("subject") == "alice"

    (tmp_path / ".namel3ss").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".namel3ss" / "permissions.yaml").write_text(
        (
            "flows:\n"
            "  demo_flow:\n"
            "    requires:\n"
            "      roles:\n"
            "        - admin\n"
        ),
        encoding="utf-8",
    )

    program = _build_program(app_path)
    with pytest.raises(Namel3ssError) as err:
        execute_program_flow(
            program,
            "demo_flow",
            input={},
            store=MemoryStore(),
            config=AppConfig(),
            identity=auth.identity,
            auth_context=auth,
        )
    assert err.value.details.get("reason_code") == "missing_role"


def test_secret_permission_enforcement_uses_rbac_roles(tmp_path: Path, monkeypatch) -> None:
    app_path = _write_app(tmp_path)
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", home.as_posix())

    add_secret(
        project_root=tmp_path,
        app_path=app_path,
        name="db_password",
        value="supersecret",
        owner="alice",
    )

    add_user(project_root=tmp_path, app_path=app_path, username="alice", roles=["developer"])
    add_user(project_root=tmp_path, app_path=app_path, username="bob", roles=["viewer"])

    (tmp_path / ".namel3ss").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".namel3ss" / "permissions.yaml").write_text(
        (
            "secrets:\n"
            "  db_password:\n"
            "    requires:\n"
            "      permissions:\n"
            "        - view_secret\n"
        ),
        encoding="utf-8",
    )

    alice_auth = resolve_auth_context(
        {"Authorization": f"Bearer {generate_token('alice')}"},
        config=AppConfig(),
        identity_schema=None,
        store=MemoryStore(),
        project_root=tmp_path.as_posix(),
        app_path=app_path.as_posix(),
    )
    bob_auth = resolve_auth_context(
        {"Authorization": f"Bearer {generate_token('bob')}"},
        config=AppConfig(),
        identity_schema=None,
        store=MemoryStore(),
        project_root=tmp_path.as_posix(),
        app_path=app_path.as_posix(),
    )

    normalized, value = resolve_secret_value(
        "db_password",
        project_root=tmp_path.as_posix(),
        app_path=app_path.as_posix(),
        identity=alice_auth.identity,
        auth_context=alice_auth,
    )
    assert normalized == "db_password"
    assert value == "supersecret"

    with pytest.raises(Namel3ssError) as err:
        resolve_secret_value(
            "db_password",
            project_root=tmp_path.as_posix(),
            app_path=app_path.as_posix(),
            identity=bob_auth.identity,
            auth_context=bob_auth,
        )
    assert err.value.details.get("reason_code") == "missing_permission"
