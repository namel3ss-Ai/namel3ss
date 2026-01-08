from __future__ import annotations

from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory_packs import (
    apply_pack_rules,
    build_pack_loaded_event,
    build_pack_merged_event,
    build_pack_overrides_event,
    load_memory_pack_catalog,
    merge_packs,
    resolve_pack_selection,
    select_packs,
)
from namel3ss.runtime.memory_packs.render import active_pack_lines, override_summary_lines, pack_provides
from namel3ss.runtime.memory_packs.sources import SourceMap, SOURCE_DEFAULT


class MemoryManagerPackMixin:
    def pack_summary(
        self,
        *,
        project_root: str | None = None,
        app_path: str | None = None,
    ) -> dict:
        project_root, app_path = self._resolve_root(project_root, app_path)
        self._ensure_packs(project_root=project_root, app_path=app_path)
        setup = self._pack_setup
        selection = self._pack_selection
        packs = setup.packs if setup else []
        sources = setup.sources if setup else SourceMap(field_sources={}, rule_sources=[], overrides=[])
        overrides = sources.overrides
        return {
            "ok": True,
            "order": [pack.pack_id for pack in packs],
            "active_lines": active_pack_lines(packs),
            "override_lines": override_summary_lines(overrides),
            "selection": {
                "mode": getattr(selection, "mode", "auto"),
                "source": getattr(selection, "source", "auto"),
                "pack_id": getattr(selection, "pack_id", None),
            },
            "packs": [
                {
                    "pack_id": pack.pack_id,
                    "pack_name": pack.pack_name,
                    "pack_version": pack.pack_version,
                    "provides": pack_provides(pack),
                    "rules_count": len(pack.rules or []),
                }
                for pack in packs
            ],
            "sources": sources.field_sources,
            "rule_sources": [{"text": entry.text, "source": entry.source} for entry in sources.rule_sources],
            "overrides": [
                {"field": entry.field, "from_source": entry.from_source, "to_source": entry.to_source}
                for entry in overrides
            ],
        }

    def _pack_overrides(self, *, field: str | None = None, prefix: str | None = None) -> bool:
        return self._pack_overrides_for(self._pack_setup, field=field, prefix=prefix)

    def _pack_overrides_for(self, setup, *, field: str | None = None, prefix: str | None = None) -> bool:
        if setup is None:
            return False
        sources = setup.sources.field_sources
        if field is not None:
            return sources.get(field, SOURCE_DEFAULT) != SOURCE_DEFAULT
        if prefix is not None:
            return any(
                name.startswith(prefix) and source != SOURCE_DEFAULT for name, source in sources.items()
            )
        return False

    def _ensure_packs(self, *, project_root: str | None, app_path: str | None) -> None:
        if self._pack_state == "ready":
            return
        if self._pack_state == "failed":
            if self._pack_error:
                raise self._pack_error
            raise Namel3ssError("Memory pack load failed.")
        if not project_root and not app_path:
            return
        try:
            catalog = load_memory_pack_catalog(project_root=project_root, app_path=app_path)
            config = load_config(
                app_path=Path(app_path) if app_path else None,
                root=Path(project_root) if project_root else None,
            )
            selection = resolve_pack_selection(config, agent_id=None)
            selected_packs = select_packs(catalog, selection=selection)
            setup = merge_packs(packs=selected_packs, overrides=catalog.overrides)
        except Namel3ssError as err:
            self._pack_state = "failed"
            self._pack_error = Namel3ssError(f"Memory pack load failed. {err}")
            raise self._pack_error
        self._pack_setup = setup
        self._pack_catalog = catalog
        self._pack_config = config
        self._pack_selection = selection
        self._pack_setups = {}
        self._pack_state = "ready"
        if setup.packs:
            for pack in setup.packs:
                self._startup_events.append(build_pack_loaded_event(pack=pack))
            self._startup_events.append(build_pack_merged_event(packs=setup.packs, sources=setup.sources))
        if setup.sources.overrides:
            self._startup_events.append(build_pack_overrides_event(overrides=setup.sources.overrides))

    def _pack_setup_for(
        self,
        *,
        agent_id: str | None,
        project_root: str | None,
        app_path: str | None,
    ):
        self._ensure_packs(project_root=project_root, app_path=app_path)
        catalog = self._pack_catalog
        config = self._pack_config
        if catalog is None or config is None:
            return self._pack_setup
        selection = resolve_pack_selection(config, agent_id=agent_id)
        if self._pack_selection and selection == self._pack_selection:
            return self._pack_setup
        cache_key = f"{selection.mode}:{selection.pack_id or ''}"
        cached = self._pack_setups.get(cache_key)
        if cached is not None:
            return cached
        selected_packs = select_packs(catalog, selection=selection)
        setup = merge_packs(packs=selected_packs, overrides=catalog.overrides)
        self._pack_setups[cache_key] = setup
        return setup

    def _apply_pack_setup(self, *, project_root: str | None, app_path: str | None) -> None:
        if self._pack_setup is None:
            return
        if self._pack_overrides(field="budgets"):
            self._budgets = list(self._pack_setup.budgets)
        if self._pack_overrides(prefix="agreement."):
            self._agreement_defaults = self._pack_setup.agreement
        else:
            self._agreement_defaults = None
        changed = apply_pack_rules(
            rules=self._pack_setup.rules,
            rule_sources=self._pack_setup.sources.rule_sources,
            semantic=self.semantic,
            factory=self._factory,
            phase_registry=self._phases,
            phase_ledger=self._ledger,
            lanes=self._pack_setup.lanes,
            phase=self._pack_setup.phase,
            project_root=project_root,
            app_path=app_path,
        )
        if changed and self._cache:
            self._cache.clear()


__all__ = ["MemoryManagerPackMixin"]
