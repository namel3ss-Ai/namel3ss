from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from namel3ss.runtime.ai.trace import AITrace


@dataclass
class ExecutionResult:
    state: Dict[str, object]
    last_value: Optional[object]
    traces: list[AITrace]
    runtime_theme: Optional[str] = None
    theme_source: Optional[str] = None
