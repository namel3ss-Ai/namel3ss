from __future__ import annotations

import sys
from types import ModuleType

from namel3ss.contract.api import contract, validate
from namel3ss.contract.builder import build_contract_pack
from namel3ss.contract.model import CONTRACT_SPEC_VERSION, Contract, ContractPack


__all__ = [
    "CONTRACT_SPEC_VERSION",
    "Contract",
    "ContractPack",
    "build_contract_pack",
    "contract",
    "validate",
]


class _CallableContractModule(ModuleType):
    def __call__(self, *args, **kwargs):
        return contract(*args, **kwargs)


sys.modules[__name__].__class__ = _CallableContractModule
