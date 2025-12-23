from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from namel3ss.ast.modules import UseDecl


@dataclass
class RunFlowStep:
    flow_name: str
    input_data: dict
    target: str
    line: int
    column: int


@dataclass
class ExpectValueIsStep:
    expected: object
    line: int
    column: int


@dataclass
class ExpectValueContainsStep:
    expected: str
    line: int
    column: int


@dataclass
class ExpectErrorContainsStep:
    expected: str
    line: int
    column: int


TestStep = RunFlowStep | ExpectValueIsStep | ExpectValueContainsStep | ExpectErrorContainsStep


@dataclass
class TestCase:
    name: str
    steps: List[TestStep]
    line: int
    column: int


@dataclass
class TestFile:
    path: str
    uses: List[UseDecl]
    tests: List[TestCase]


@dataclass
class TestResult:
    name: str
    file: str
    status: str
    duration_ms: float
    error: Optional[str] = None
