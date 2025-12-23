from __future__ import annotations


def record_state_path(record_name: str) -> list[str]:
    return [part.lower() for part in record_name.split(".") if part]


def get_state_record(state: dict, record_name: str) -> object:
    path = record_state_path(record_name)
    cursor: object = state
    for segment in path:
        if not isinstance(cursor, dict):
            return None
        if segment not in cursor:
            return None
        cursor = cursor[segment]
    return cursor


def set_state_record(state: dict, record_name: str, values: dict) -> None:
    path = record_state_path(record_name)
    if not path:
        return
    cursor: dict = state
    for segment in path[:-1]:
        if segment not in cursor or not isinstance(cursor[segment], dict):
            cursor[segment] = {}
        cursor = cursor[segment]
    cursor[path[-1]] = values
