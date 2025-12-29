from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StoreOutcome:
    """Facts about store transactions during a run."""

    began: bool  # store.begin completed without error
    committed: bool  # store.commit completed without error
    commit_failed: bool  # store.commit raised an error
    rolled_back: bool  # store.rollback completed without error
    rollback_failed: bool  # store.rollback raised an error

    def as_dict(self) -> dict[str, object]:
        return {
            "began": self.began,
            "committed": self.committed,
            "commit_failed": self.commit_failed,
            "rolled_back": self.rolled_back,
            "rollback_failed": self.rollback_failed,
        }


@dataclass(frozen=True)
class StateOutcome:
    """Facts about state load/save during a run."""

    loaded_from_store: bool | None  # True if loaded from store, False if provided, None if unknown
    save_attempted: bool  # store.save_state was called
    save_succeeded: bool  # store.save_state completed without error
    save_failed: bool  # store.save_state raised an error

    def as_dict(self) -> dict[str, object]:
        return {
            "loaded_from_store": self.loaded_from_store,
            "save_attempted": self.save_attempted,
            "save_succeeded": self.save_succeeded,
            "save_failed": self.save_failed,
        }


@dataclass(frozen=True)
class MemoryOutcome:
    """Facts about memory persistence during a run."""

    persist_attempted: bool  # memory.persist was called
    persist_succeeded: bool  # memory.persist completed without error
    persist_failed: bool  # memory.persist raised an error
    skipped_reason: str | None  # reason persistence was skipped when known

    def as_dict(self) -> dict[str, object]:
        return {
            "persist_attempted": self.persist_attempted,
            "persist_succeeded": self.persist_succeeded,
            "persist_failed": self.persist_failed,
            "skipped_reason": self.skipped_reason,
        }


@dataclass(frozen=True)
class RunOutcome:
    """Outcome summary for a single flow run."""

    status: str  # ok | partial | error
    flow_name: str
    store: StoreOutcome
    state: StateOutcome
    memory: MemoryOutcome
    record_changes_count: int  # number of record changes recorded
    execution_steps_count: int  # number of execution steps recorded
    traces_count: int  # number of trace entries recorded
    what_did_not_happen: tuple[str, ...]  # deterministic list of skipped/failed actions

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "flow_name": self.flow_name,
            "store": self.store.as_dict(),
            "state": self.state.as_dict(),
            "memory": self.memory.as_dict(),
            "record_changes_count": self.record_changes_count,
            "execution_steps_count": self.execution_steps_count,
            "traces_count": self.traces_count,
            "what_did_not_happen": list(self.what_did_not_happen),
        }


@dataclass(frozen=True)
class OutcomePack:
    """Serializable pack written after each run."""

    outcome: RunOutcome
    summary: dict

    def as_dict(self) -> dict[str, object]:
        return {
            "outcome": self.outcome.as_dict(),
            "summary": dict(self.summary),
        }


__all__ = [
    "MemoryOutcome",
    "OutcomePack",
    "RunOutcome",
    "StateOutcome",
    "StoreOutcome",
]
