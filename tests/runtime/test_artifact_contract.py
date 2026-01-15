from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.runtime.artifact_contract import ArtifactContract, ArtifactContractError


def test_artifact_contract_rejects_escape(tmp_path: Path) -> None:
    contract = ArtifactContract(tmp_path / ".namel3ss")
    target = contract.prepare_file("run/last.json")
    assert target.exists() is False
    assert str(target).startswith(str(contract.root))

    with pytest.raises(ArtifactContractError):
        contract.resolve("../outside.json")
