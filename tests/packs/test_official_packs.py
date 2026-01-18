from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from namel3ss.runtime.packs.authoring_validate import validate_pack
from namel3ss.runtime.packs.manifest import parse_pack_manifest
from namel3ss.runtime.packs.trust_store import TrustedKey, add_trusted_key
from namel3ss.runtime.packs.verification import load_pack_verification


OFFICIAL_ROOT = Path(__file__).resolve().parents[2] / "packs" / "official"
OFFICIAL_KEY_ID = "official.key"
OFFICIAL_KEY_TEXT = "official-secret"


def test_official_pack_structure_and_signature(tmp_path: Path) -> None:
    add_trusted_key(tmp_path, TrustedKey(key_id=OFFICIAL_KEY_ID, public_key=OFFICIAL_KEY_TEXT))
    pack_dirs = _pack_dirs()
    assert pack_dirs
    for pack_dir in pack_dirs:
        _assert_required_files(pack_dir)
        _assert_cases_file(pack_dir)
        validation = validate_pack(pack_dir)
        assert not validation.errors
        manifest_text = (pack_dir / "pack.yaml").read_text(encoding="utf-8")
        tools_text = None
        tools_path = pack_dir / "tools.yaml"
        if tools_path.exists():
            tools_text = tools_path.read_text(encoding="utf-8")
        verification = load_pack_verification(pack_dir, manifest_text, tools_text, app_root=tmp_path)
        assert verification.verified is True
        assert verification.key_id == OFFICIAL_KEY_ID


def test_official_pack_cases(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    for pack_dir in _pack_dirs():
        manifest = parse_pack_manifest(pack_dir / "pack.yaml")
        entrypoints = manifest.entrypoints or {}
        cases = _load_cases(pack_dir)
        for idx, case in enumerate(cases):
            tool_name = case["tool"]
            payload = case["payload"]
            expect = case["expect"]
            binding = entrypoints.get(tool_name)
            assert binding is not None
            module_path, func_name = _entrypoint_path(pack_dir, binding.entry)
            func = _load_entrypoint(module_path, f"{pack_dir.name}_{idx}", func_name)
            result = func(payload)
            assert result == expect


def _pack_dirs() -> list[Path]:
    return sorted([path for path in OFFICIAL_ROOT.iterdir() if path.is_dir()])


def _assert_required_files(pack_dir: Path) -> None:
    required = ["pack.yaml", "capabilities.yaml", "intent.md", "README.md", "signature.txt"]
    for name in required:
        assert (pack_dir / name).exists()


def _assert_cases_file(pack_dir: Path) -> None:
    cases_path = pack_dir / "tests" / "cases.json"
    assert cases_path.exists()
    data = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = data.get("cases")
    assert isinstance(cases, list) and cases


def _load_cases(pack_dir: Path) -> list[dict[str, object]]:
    data = json.loads((pack_dir / "tests" / "cases.json").read_text(encoding="utf-8"))
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise AssertionError("Pack test cases must be a list")
    return cases


def _entrypoint_path(pack_dir: Path, entry: str) -> tuple[Path, str]:
    if ":" not in entry:
        raise AssertionError("Entrypoint must include module and function")
    module_path, func_name = entry.split(":", 1)
    path = pack_dir / (module_path.replace(".", "/") + ".py")
    return path, func_name


def _load_entrypoint(path: Path, module_name: str, func_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load module at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    func = getattr(module, func_name, None)
    if func is None or not callable(func):
        raise AssertionError(f"Entrypoint {func_name} is missing in {path}")
    return func
