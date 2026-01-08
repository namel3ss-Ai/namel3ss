from __future__ import annotations

from typing import Dict

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory.contract import MemoryClock, MemoryIdGenerator, MemoryItemFactory
from namel3ss.runtime.memory.manager_admin import MemoryManagerAdminMixin
from namel3ss.runtime.memory.manager_cache import MemoryManagerCacheMixin
from namel3ss.runtime.memory.manager_packs import MemoryManagerPackMixin
from namel3ss.runtime.memory.manager_policy import MemoryManagerPolicyMixin
from namel3ss.runtime.memory.manager_restore import MemoryManagerRestoreMixin
from namel3ss.runtime.memory.manager_runtime import MemoryManagerRuntimeMixin
from namel3ss.runtime.memory_budget.defaults import DEFAULT_CACHE_MAX_ENTRIES, default_budget_configs
from namel3ss.runtime.memory_cache import MemoryCacheStore
from namel3ss.runtime.memory_handoff import HandoffStore
from namel3ss.runtime.memory_packs import AgreementDefaults, EffectiveMemoryPackSetup
from namel3ss.runtime.memory.profile import ProfileMemory
from namel3ss.runtime.memory.semantic import SemanticMemory
from namel3ss.runtime.memory.short_term import ShortTermMemory
from namel3ss.runtime.memory.spaces import SpaceContext, resolve_space_context
from namel3ss.runtime.memory_timeline.phase import PhaseRegistry
from namel3ss.runtime.memory_timeline.snapshot import PhaseLedger
from namel3ss.runtime.memory_agreement import ProposalStore
from namel3ss.runtime.memory_trust.model import TrustRules


class MemoryManager(
    MemoryManagerRuntimeMixin,
    MemoryManagerAdminMixin,
    MemoryManagerPolicyMixin,
    MemoryManagerPackMixin,
    MemoryManagerRestoreMixin,
    MemoryManagerCacheMixin,
):
    def __init__(self, *, project_root: str | None = None, app_path: str | None = None) -> None:
        clock = MemoryClock()
        ids = MemoryIdGenerator()
        factory = MemoryItemFactory(clock=clock, id_generator=ids)
        self._clock = clock
        self._ids = ids
        self._factory = factory
        self._phases = PhaseRegistry(clock=clock)
        self._ledger = PhaseLedger()
        self._budgets = default_budget_configs()
        self._cache = MemoryCacheStore(max_entries=DEFAULT_CACHE_MAX_ENTRIES)
        self._cache_versions: dict[tuple[str, str], int] = {}
        self._trust_rules: TrustRules | None = None
        self._pack_state = "pending"
        self._pack_error: Namel3ssError | None = None
        self._pack_setup: EffectiveMemoryPackSetup | None = None
        self._pack_catalog = None
        self._pack_config = None
        self._pack_selection = None
        self._pack_setups: dict[str, EffectiveMemoryPackSetup] = {}
        self._agreement_defaults: AgreementDefaults | None = None
        self._restore_state = "pending"
        self._restore_error: Namel3ssError | None = None
        self._startup_events: list[dict] = []
        self._default_project_root = project_root
        self._default_app_path = app_path
        self.agreements = ProposalStore()
        self.handoffs = HandoffStore()
        self.short_term = ShortTermMemory(factory=factory)
        self.profile = ProfileMemory(factory=factory)
        self.semantic = SemanticMemory(factory=factory)

    def space_context(
        self,
        state: Dict[str, object],
        *,
        identity: Dict[str, object] | None = None,
        project_root: str | None = None,
        app_path: str | None = None,
    ) -> SpaceContext:
        return resolve_space_context(
            state,
            identity=identity,
            project_root=project_root,
            app_path=app_path,
        )

    def session_id(
        self,
        state: Dict[str, object],
        *,
        identity: Dict[str, object] | None = None,
        project_root: str | None = None,
        app_path: str | None = None,
    ) -> str:
        return self.space_context(
            state,
            identity=identity,
            project_root=project_root,
            app_path=app_path,
        ).session_id

    def _resolve_root(
        self,
        project_root: str | None,
        app_path: str | None,
    ) -> tuple[str | None, str | None]:
        return project_root or self._default_project_root, app_path or self._default_app_path


__all__ = ["MemoryManager"]
