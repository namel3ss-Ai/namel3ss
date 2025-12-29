import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory_packs.format import MemoryOverrides, MemoryPack, PackTrustSettings
from namel3ss.runtime.memory_packs.loader import load_memory_packs
from namel3ss.runtime.memory_packs.merge import merge_packs
from namel3ss.runtime.memory_packs.render import (
    active_pack_lines,
    override_summary_lines,
    pack_order_lines,
    pack_loaded_lines,
)
from namel3ss.runtime.memory_packs.sources import OverrideEntry
from namel3ss.runtime.memory_packs.validate import validate_overrides_payload, validate_pack_payload


def test_pack_validation_rejects_unknown_field():
    payload = {
        "format_version": "memory_pack_v1",
        "pack_id": "base",
        "pack_name": "Base pack",
        "pack_version": "1.0.0",
        "rules": ["Only approvers can approve team proposals"],
        "unexpected": "nope",
    }
    with pytest.raises(Namel3ssError):
        validate_pack_payload(payload, rules=None, source_path="pack.toml")


def test_override_validation_rejects_unknown_field():
    payload = {"unexpected": "nope"}
    with pytest.raises(Namel3ssError):
        validate_overrides_payload(payload, source_path="memory_overrides.toml")


def test_pack_merge_ordering_and_sources():
    pack_base = MemoryPack(
        pack_id="base",
        pack_name="Base pack",
        pack_version="1.0.0",
        rules=None,
        trust=PackTrustSettings(who_can_propose="contributor"),
        agreement=None,
        budgets=None,
        lanes=None,
        phase=None,
        source_path="base",
    )
    pack_team = MemoryPack(
        pack_id="team",
        pack_name="Team pack",
        pack_version="1.0.0",
        rules=None,
        trust=PackTrustSettings(who_can_propose="approver"),
        agreement=None,
        budgets=None,
        lanes=None,
        phase=None,
        source_path="team",
    )
    setup = merge_packs(packs=[pack_base, pack_team], overrides=None)
    assert setup.trust.who_can_propose == "approver"
    assert setup.sources.field_sources["trust.who_can_propose"] == "pack team"


def test_pack_overrides_are_tracked():
    pack_base = MemoryPack(
        pack_id="base",
        pack_name="Base pack",
        pack_version="1.0.0",
        rules=None,
        trust=PackTrustSettings(who_can_propose="contributor"),
        agreement=None,
        budgets=None,
        lanes=None,
        phase=None,
        source_path="base",
    )
    overrides = MemoryOverrides(
        rules=None,
        trust=PackTrustSettings(who_can_propose="owner"),
        agreement=None,
        budgets=None,
        lanes=None,
        phase=None,
        source_path="overrides",
    )
    setup = merge_packs(packs=[pack_base], overrides=overrides)
    assert setup.trust.who_can_propose == "owner"
    assert setup.sources.overrides
    entry = setup.sources.overrides[0]
    assert entry.field == "trust.who_can_propose"
    assert entry.to_source == "local override"


def test_pack_rules_merge_and_sources():
    pack_base = MemoryPack(
        pack_id="base",
        pack_name="Base pack",
        pack_version="1.0.0",
        rules=["Rule A", "Rule B"],
        trust=None,
        agreement=None,
        budgets=None,
        lanes=None,
        phase=None,
        source_path="base",
    )
    pack_team = MemoryPack(
        pack_id="team",
        pack_name="Team pack",
        pack_version="1.0.0",
        rules=["Rule B", "Rule C"],
        trust=None,
        agreement=None,
        budgets=None,
        lanes=None,
        phase=None,
        source_path="team",
    )
    setup = merge_packs(packs=[pack_base, pack_team], overrides=None)
    assert setup.rules == ["Rule A", "Rule B", "Rule C"]
    sources = [(entry.text, entry.source) for entry in setup.sources.rule_sources]
    assert sources == [
        ("Rule A", "pack base"),
        ("Rule B", "pack team"),
        ("Rule C", "pack team"),
    ]
    assert setup.sources.field_sources["rules"] == "pack team"


def test_pack_rules_overrides_are_tracked():
    pack_base = MemoryPack(
        pack_id="base",
        pack_name="Base pack",
        pack_version="1.0.0",
        rules=["Rule A", "Rule B"],
        trust=None,
        agreement=None,
        budgets=None,
        lanes=None,
        phase=None,
        source_path="base",
    )
    overrides = MemoryOverrides(
        rules=["Rule B", "Rule D"],
        trust=None,
        agreement=None,
        budgets=None,
        lanes=None,
        phase=None,
        source_path="overrides",
    )
    setup = merge_packs(packs=[pack_base], overrides=overrides)
    assert setup.rules == ["Rule A", "Rule B", "Rule D"]
    sources = [(entry.text, entry.source) for entry in setup.sources.rule_sources]
    assert sources == [
        ("Rule A", "pack base"),
        ("Rule B", "local override"),
        ("Rule D", "local override"),
    ]
    override_fields = [entry.field for entry in setup.sources.overrides]
    assert "rules" in override_fields


def test_pack_loader_orders_by_folder_name(tmp_path):
    packs_root = tmp_path / "packs" / "memory"
    _write_pack(packs_root / "b_pack", pack_id="alpha", pack_name="Alpha pack")
    _write_pack(packs_root / "a_pack", pack_id="beta", pack_name="Beta pack")
    result = load_memory_packs(project_root=str(tmp_path), app_path=None)
    assert [pack.pack_id for pack in result.packs] == ["beta", "alpha"]


def test_pack_render_lines_are_bracketless():
    pack = MemoryPack(
        pack_id="base",
        pack_name="Base pack",
        pack_version="1.0.0",
        rules=None,
        trust=None,
        agreement=None,
        budgets=None,
        lanes=None,
        phase=None,
        source_path="base",
    )
    overrides = [
        OverrideEntry(
            field="trust.who_can_propose",
            from_source="pack base",
            to_source="local override",
        )
    ]
    lines = []
    lines.extend(active_pack_lines([pack]))
    lines.extend(pack_order_lines([pack]))
    lines.extend(pack_loaded_lines(pack))
    lines.extend(override_summary_lines(overrides))
    assert _no_brackets(lines)


def _no_brackets(lines: list[str]) -> bool:
    joined = "".join(lines)
    return all(ch not in joined for ch in "{}[]()")


def _write_pack(pack_dir, *, pack_id: str, pack_name: str) -> None:
    pack_dir.mkdir(parents=True, exist_ok=True)
    content = "\n".join(
        [
            'format_version = "memory_pack_v1"',
            f'pack_id = "{pack_id}"',
            f'pack_name = "{pack_name}"',
            'pack_version = "1.0.0"',
        ]
    )
    (pack_dir / "pack.toml").write_text(content + "\n", encoding="utf-8")
