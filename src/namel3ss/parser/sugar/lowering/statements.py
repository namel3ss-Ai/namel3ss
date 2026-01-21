from __future__ import annotations

from namel3ss.parser.sugar.lowering.stmt_lower_blocks import (
    _CAMEL_BOUNDARY,
    _lower_clear,
    _lower_latest_let,
    _lower_notice,
    _lower_require_latest,
    _lower_save_record,
    _record_missing_slug,
    _record_results_slug,
)
from namel3ss.parser.sugar.lowering.stmt_lower_core import _lower_statement, _lower_statements
