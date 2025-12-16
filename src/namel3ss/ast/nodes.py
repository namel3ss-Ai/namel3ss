from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Union

from namel3ss.ast.agents import AgentDecl
from namel3ss.ast.ai import AIDecl, AIMemory
from namel3ss.ast.base import Node
from namel3ss.ast.expressions import (
    Assignable,
    AttrAccess,
    BinaryOp,
    Comparison,
    Expression,
    Literal,
    StatePath,
    UnaryOp,
    VarReference,
)
from namel3ss.ast.pages import ButtonItem, FormItem, PageDecl, PageItem, TableItem, TextItem, TitleItem
from namel3ss.ast.program import Flow, Program
from namel3ss.ast.statements import (
    AskAIStmt,
    Find,
    ForEach,
    If,
    Let,
    Match,
    MatchCase,
    ParallelAgentEntry,
    Repeat,
    Return,
    RunAgentStmt,
    RunAgentsParallelStmt,
    Save,
    Set,
    Statement,
    TryCatch,
)
from namel3ss.ast.tool import ToolDecl
from namel3ss.ast.records import FieldConstraint, FieldDecl, RecordDecl

__all__ = [
    "Node",
    "Flow",
    "Program",
    "Statement",
    "Let",
    "Set",
    "If",
    "Return",
    "AskAIStmt",
    "RunAgentStmt",
    "ParallelAgentEntry",
    "RunAgentsParallelStmt",
    "Repeat",
    "ForEach",
    "MatchCase",
    "Match",
    "TryCatch",
    "Save",
    "Find",
    "Expression",
    "Literal",
    "VarReference",
    "AttrAccess",
    "StatePath",
    "UnaryOp",
    "BinaryOp",
    "Comparison",
    "Assignable",
    "FieldConstraint",
    "FieldDecl",
    "RecordDecl",
    "PageItem",
    "TitleItem",
    "TextItem",
    "FormItem",
    "TableItem",
    "ButtonItem",
    "PageDecl",
    "AIDecl",
    "AIMemory",
    "ToolDecl",
    "AgentDecl",
]
