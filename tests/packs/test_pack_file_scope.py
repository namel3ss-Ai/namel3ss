from __future__ import annotations

from pathlib import Path

import pytest

import namel3ss.tool_packs.file as file_pack


def test_pack_file_scope_blocks_absolute(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    outside = tmp_path.parent / "outside.txt"
    with pytest.raises(ValueError):
        file_pack.write_text({"path": str(outside), "text": "no"})
