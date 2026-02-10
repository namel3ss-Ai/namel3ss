from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from namel3ss.errors.base import Namel3ssError


@dataclass(frozen=True)
class PluginRuntimeAPI:
    state: Mapping[str, object]
    actions: Mapping[str, object]
    theme_tokens: Mapping[str, object]
    translations: Mapping[str, object]

    def read_state(self, path: str) -> object | None:
        if not isinstance(path, str) or not path.strip():
            raise Namel3ssError("State path must be a non-empty string.")
        current: object = self.state
        for segment in path.split("."):
            if not isinstance(current, Mapping):
                return None
            if segment not in current:
                return None
            current = current[segment]
        return current

    def has_action(self, action_id: str) -> bool:
        return isinstance(action_id, str) and action_id in self.actions

    def theme_token(self, token_name: str) -> object | None:
        if not isinstance(token_name, str):
            return None
        return self.theme_tokens.get(token_name)

    def translate(self, key: str, default: str | None = None) -> str:
        if not isinstance(key, str) or not key:
            return default or ""
        value = self.translations.get(key)
        if isinstance(value, str):
            return value
        return default or key


def build_plugin_runtime_api(
    *,
    state: Mapping[str, object] | None,
    actions: Mapping[str, object] | None,
    theme_tokens: Mapping[str, object] | None,
    translations: Mapping[str, object] | None,
) -> PluginRuntimeAPI:
    return PluginRuntimeAPI(
        state=dict(state or {}),
        actions=dict(actions or {}),
        theme_tokens=dict(theme_tokens or {}),
        translations=dict(translations or {}),
    )


__all__ = ["PluginRuntimeAPI", "build_plugin_runtime_api"]
