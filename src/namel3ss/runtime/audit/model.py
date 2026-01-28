from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DecisionStep:
    id: str
    category: str
    subject: str | None
    inputs: dict = field(default_factory=dict)
    rules: list[object] = field(default_factory=list)
    outcome: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "subject": self.subject,
            "inputs": dict(self.inputs),
            "rules": list(self.rules),
            "outcome": dict(self.outcome),
        }


@dataclass(frozen=True)
class DecisionModel:
    inputs: dict
    decisions: list[DecisionStep]
    policies: dict
    outcomes: dict

    def as_dict(self) -> dict:
        return {
            "inputs": dict(self.inputs),
            "decisions": [step.as_dict() for step in self.decisions],
            "policies": dict(self.policies),
            "outcomes": dict(self.outcomes),
        }


__all__ = ["DecisionModel", "DecisionStep"]
