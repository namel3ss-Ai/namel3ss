from __future__ import annotations

import json
from pathlib import Path

from namel3ss.studio import security_api


SOURCE = '''tool "get json from web":
  implemented using python

  input:
    url is text

  output:
    status is number
    headers is json
    data is json

flow "demo":
  return "ok"
'''


def test_security_payload_includes_guarantees(tmp_path: Path) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text(SOURCE, encoding="utf-8")
    payload = security_api.get_security_payload(str(app_path))
    assert payload["ok"] is True
    assert isinstance(payload.get("tools"), list)
    tool = next(item for item in payload["tools"] if item.get("tool_name") == "get json from web")
    assert "guarantees" in tool
    assert "guarantee_sources" in tool
    assert "coverage" in tool
    assert "sandbox" in tool
    assert tool["unsafe_override"] is False
    json.dumps(payload)
