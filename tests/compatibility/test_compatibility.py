from __future__ import annotations

from namel3ss.cli.main import main as cli_main
from namel3ss.compatibility import apply_migration, plan_migration
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.resources import studio_web_root, templates_root
from namel3ss.runtime.run_pipeline import build_flow_payload, finalize_run_payload
from namel3ss.studio.api import get_version_payload
from namel3ss.version import get_version


SUPPORTED_SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''

UNSUPPORTED_SOURCE = '''spec is "9.9"

flow "demo":
  return "ok"
'''

LEGACY_SOURCE = '''spec is "0.9"

page "home":
  button "Run" calls flow "demo"

flow "demo":
  return "ok"
'''

UPGRADE_SOURCE = '''spec is "0.9"

flow "demo":
  return "ok"
'''


def _run_payload(source: str):
    program = lower_program(parse(source))
    outcome = build_flow_payload(program, "demo")
    payload = finalize_run_payload(outcome.payload, [])
    return outcome, payload


def test_version_consistency_cli_studio(capsys):
    version = get_version()
    assert get_version_payload()["version"] == version

    assert cli_main(["--version"]) == 0
    out = capsys.readouterr().out.strip()
    assert out == f"namel3ss {version}"

    assert cli_main(["version"]) == 0
    out = capsys.readouterr().out.strip()
    assert out == f"namel3ss {version}"


def test_spec_validation_supported_and_blocked():
    outcome, payload = _run_payload(SUPPORTED_SOURCE)
    assert outcome.error is None
    assert payload["ok"] is True
    assert payload["contract"]["errors"] == []

    outcome, payload = _run_payload(UNSUPPORTED_SOURCE)
    assert outcome.error is not None
    errors = payload["contract"]["errors"]
    assert errors
    assert errors[0]["category"] == "policy"
    assert errors[0]["code"] == "spec.unsupported"


def test_migration_is_idempotent():
    plan = plan_migration(LEGACY_SOURCE, from_version=None, to_version="1.0")
    result = apply_migration(LEGACY_SOURCE, plan)
    assert result.changed

    second_plan = plan_migration(result.source, from_version=None, to_version="1.0")
    second = apply_migration(result.source, second_plan)
    assert second.changed is False
    assert second.source == result.source


def test_upgrade_simulation_requires_migration_then_runs():
    outcome, payload = _run_payload(UPGRADE_SOURCE)
    assert outcome.error is not None
    errors = payload["contract"]["errors"]
    assert errors and errors[0]["code"] == "spec.migration_required"

    plan = plan_migration(UPGRADE_SOURCE, from_version=None, to_version="1.0")
    migrated = apply_migration(UPGRADE_SOURCE, plan).source
    outcome, payload = _run_payload(migrated)
    assert outcome.error is None
    assert payload["ok"] is True


def test_packaging_assets_present():
    templates = templates_root()
    assert (templates / "starter" / "app.ai").exists()
    assert (templates / "clear_orders" / "app.ai").exists()

    web_root = studio_web_root()
    for name in ("index.html", "app.js", "styles.css"):
        assert (web_root / name).exists()
