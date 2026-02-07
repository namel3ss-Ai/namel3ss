from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.utils.numbers import is_number

from .loader import load_plugin_schema, resolve_plugin_directories
from .sandbox import load_sandboxed_renderer
from .schema import UIPluginComponentSchema, UIPluginSchema


@dataclass(frozen=True)
class UIPluginComponentBinding:
    plugin_name: str
    schema: UIPluginComponentSchema
    render: object


class UIPluginRegistry:
    def __init__(
        self,
        *,
        plugins: dict[str, UIPluginSchema],
        components: dict[str, UIPluginComponentBinding],
    ) -> None:
        self._plugins = dict(plugins)
        self._components = dict(components)

    @property
    def plugin_names(self) -> tuple[str, ...]:
        return tuple(self._plugins.keys())

    def has_component(self, name: str) -> bool:
        return name in self._components

    def component_schema(self, name: str) -> UIPluginComponentSchema | None:
        binding = self._components.get(name)
        return binding.schema if binding is not None else None

    def component_plugin_name(self, name: str) -> str | None:
        binding = self._components.get(name)
        return binding.plugin_name if binding is not None else None

    def validate_component_usage(
        self,
        component_name: str,
        properties: list[object],
        flow_names: set[str],
        *,
        line: int | None,
        column: int | None,
    ) -> tuple[str, list[tuple[str, object]]]:
        binding = self._components.get(component_name)
        if binding is None:
            raise Namel3ssError(
                f"Component {component_name} is not defined. Did you forget to use plugin?",
                line=line,
                column=column,
            )
        schema = binding.schema

        declared: dict[str, tuple[object, int | None, int | None]] = {}
        for prop in properties:
            name = str(getattr(prop, "name", "") or "")
            if not name:
                raise Namel3ssError(
                    f"Component '{component_name}' has a property without a name.",
                    line=getattr(prop, "line", line),
                    column=getattr(prop, "column", column),
                )
            value = getattr(prop, "value", None)
            prop_line = getattr(prop, "line", line)
            prop_column = getattr(prop, "column", column)
            if name in declared:
                raise Namel3ssError(
                    f"Component '{component_name}' property '{name}' is declared more than once.",
                    line=prop_line,
                    column=prop_column,
                )
            declared[name] = (value, prop_line, prop_column)

        for required_name, required_spec in schema.props.items():
            if required_spec.required and required_name not in declared:
                raise Namel3ssError(
                    f"Component '{component_name}' is missing required property '{required_name}'.",
                    line=line,
                    column=column,
                )

        normalized: list[tuple[str, object]] = []
        for name, (value, prop_line, prop_column) in declared.items():
            if name in schema.events:
                if not isinstance(value, str) or not value:
                    raise Namel3ssError(
                        f"Event '{name}' on component '{component_name}' must bind to a flow name.",
                        line=prop_line,
                        column=prop_column,
                    )
                if value not in flow_names:
                    raise Namel3ssError(
                        f"Event '{name}' on component '{component_name}' references unknown flow '{value}'.",
                        line=prop_line,
                        column=prop_column,
                    )
                normalized.append((name, value))
                continue

            spec = schema.props.get(name)
            if spec is None:
                allowed = sorted([*schema.props.keys(), *schema.events])
                suffix = f" Allowed: {', '.join(allowed)}." if allowed else ""
                raise Namel3ssError(
                    f"Unknown property '{name}' on component '{component_name}'.{suffix}",
                    line=prop_line,
                    column=prop_column,
                )
            if not _value_matches_type(value, spec.type_name):
                raise Namel3ssError(
                    f"Property '{name}' on component '{component_name}' must be {spec.type_name}.",
                    line=prop_line,
                    column=prop_column,
                )
            normalized.append((name, value))
        return binding.plugin_name, normalized

    def render_component(self, component_name: str, *, props: dict[str, object], state: dict) -> list[dict]:
        binding = self._components.get(component_name)
        if binding is None:
            raise Namel3ssError(f"Component {component_name} is not defined. Did you forget to use plugin?")
        renderer = binding.render
        return renderer(props, state)


def load_ui_plugin_registry(
    *,
    plugin_names: tuple[str, ...],
    project_root: str | Path | None,
    app_path: str | Path | None,
    allowed_capabilities: tuple[str, ...],
) -> UIPluginRegistry:
    if not plugin_names:
        return UIPluginRegistry(plugins={}, components={})

    if not _plugins_enabled():
        raise Namel3ssError(
            "UI plug-ins are disabled by configuration. Set N3_UI_PLUGINS_ENABLED=true to enable them."
        )

    directories = resolve_plugin_directories(project_root=project_root, app_path=app_path)
    plugins: dict[str, UIPluginSchema] = {}
    components: dict[str, UIPluginComponentBinding] = {}
    allowed = {str(entry).strip().lower() for entry in allowed_capabilities}

    for plugin_name in plugin_names:
        schema = load_plugin_schema(plugin_name, directories=directories)
        _ensure_plugin_capabilities(schema, allowed_capabilities=allowed)
        renderer = load_sandboxed_renderer(schema.module_path)
        plugins[schema.name] = schema
        for component in schema.components:
            existing = components.get(component.name)
            if existing is not None:
                raise Namel3ssError(
                    f"Duplicate component {component.name} provided by plug-ins {existing.plugin_name} and {schema.name}."
                )
            components[component.name] = UIPluginComponentBinding(
                plugin_name=schema.name,
                schema=component,
                render=renderer,
            )

    return UIPluginRegistry(plugins=plugins, components=components)


def _plugins_enabled() -> bool:
    raw = os.environ.get("N3_UI_PLUGINS_ENABLED")
    token = str(raw or "").strip().lower()
    if token in {"", "1", "true", "yes", "on"}:
        return True
    if token in {"0", "false", "no", "off"}:
        return False
    return True


def _ensure_plugin_capabilities(schema: UIPluginSchema, *, allowed_capabilities: set[str]) -> None:
    if not schema.capabilities:
        return
    missing = [entry for entry in schema.capabilities if entry not in allowed_capabilities]
    if not missing:
        return
    missing_text = ", ".join(sorted(missing))
    raise Namel3ssError(
        f"UI plug-in '{schema.name}' requires missing capabilities: {missing_text}."
    )


def _value_matches_type(value: object, type_name: str) -> bool:
    if isinstance(value, ast.PatternParamRef):
        return True
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "number":
        return is_number(value) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "state_path":
        return isinstance(value, (ast.StatePath, ir.StatePath))
    return False


__all__ = [
    "UIPluginComponentBinding",
    "UIPluginRegistry",
    "load_ui_plugin_registry",
]
