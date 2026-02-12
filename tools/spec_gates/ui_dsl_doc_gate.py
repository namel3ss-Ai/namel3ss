from __future__ import annotations

# Compatibility shim keeps existing imports stable while the classifier module is the source of truth.
from tools.spec_gates.ui_dsl_classifier import classify_ui_dsl_semantic_files

__all__ = ["classify_ui_dsl_semantic_files"]
