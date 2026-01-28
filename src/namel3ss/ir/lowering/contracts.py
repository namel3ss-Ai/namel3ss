from __future__ import annotations

from typing import Dict, List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.functions.model import FunctionParam, FunctionSignature
from namel3ss.ir.model.contracts import ContractDecl


def lower_flow_contracts(contracts: List[ast.ContractDecl]) -> Dict[str, ContractDecl]:
    contract_map: Dict[str, ContractDecl] = {}
    for contract in contracts:
        if contract.kind != "flow":
            raise Namel3ssError(
                f"Unsupported contract kind '{contract.kind}'",
                line=contract.line,
                column=contract.column,
            )
        if contract.name in contract_map:
            raise Namel3ssError(
                f"Duplicate contract declaration '{contract.name}'",
                line=contract.line,
                column=contract.column,
            )
        inputs = [
            FunctionParam(
                name=param.name,
                type_name=param.type_name,
                required=param.required,
                line=param.line,
                column=param.column,
            )
            for param in contract.signature.inputs
        ]
        outputs = [
            FunctionParam(
                name=param.name,
                type_name=param.type_name,
                required=param.required,
                line=param.line,
                column=param.column,
            )
            for param in contract.signature.outputs or []
        ]
        signature = FunctionSignature(
            inputs=inputs,
            outputs=outputs,
            line=contract.signature.line,
            column=contract.signature.column,
        )
        contract_map[contract.name] = ContractDecl(
            kind=contract.kind,
            name=contract.name,
            signature=signature,
            line=contract.line,
            column=contract.column,
        )
    return contract_map


__all__ = ["lower_flow_contracts"]
