import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory.contract import validate_memory_item


def _base_item() -> dict:
    return {
        "id": "session-1:short_term:1",
        "kind": "short_term",
        "text": "hello",
        "source": "user",
        "created_at": 1,
        "importance": 0,
        "scope": "session",
        "meta": {},
    }


def test_validate_memory_item_missing_fields():
    item = _base_item()
    item.pop("id")
    with pytest.raises(Namel3ssError):
        validate_memory_item(item)


def test_validate_memory_item_invalid_kind():
    item = _base_item()
    item["kind"] = "unknown"
    with pytest.raises(Namel3ssError):
        validate_memory_item(item)


def test_validate_memory_item_invalid_scope():
    item = _base_item()
    item["scope"] = "global"
    with pytest.raises(Namel3ssError):
        validate_memory_item(item)


def test_validate_memory_item_non_deterministic_created_at():
    item = _base_item()
    item["created_at"] = 1.25
    with pytest.raises(Namel3ssError):
        validate_memory_item(item)
