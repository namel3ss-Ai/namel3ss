"""
Namel3ss: an English-first, AI-native full-stack programming language engine package.
"""

__all__ = ["Contract", "contract", "validate"]


def contract(*args, **kwargs):
    from namel3ss.contract.api import contract as _contract

    return _contract(*args, **kwargs)


def validate(*args, **kwargs):
    from namel3ss.contract.api import validate as _validate

    return _validate(*args, **kwargs)


def __getattr__(name: str):
    if name == "Contract":
        from namel3ss.contract.model import Contract

        return Contract
    raise AttributeError(f"module 'namel3ss' has no attribute {name!r}")
