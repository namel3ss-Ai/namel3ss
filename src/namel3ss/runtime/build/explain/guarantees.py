from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple


def infer_guarantees(project_root: Path) -> Tuple[List[str], List[str], Dict[str, Any], Dict[str, Any]]:
    return ([], [], {}, {})


__all__ = ["infer_guarantees"]
