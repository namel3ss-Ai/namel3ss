from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

from namel3ss.runtime.backend.upload_store import store_upload
from namel3ss.traces.schema import TraceEventType
from tests.conftest import run_flow


def _flow_call_events(result) -> list[dict]:
    return [
        event
        for event in result.traces
        if isinstance(event, dict)
        and event.get("type") in {TraceEventType.FLOW_CALL_STARTED, TraceEventType.FLOW_CALL_FINISHED}
    ]


def test_flow_call_is_deterministic_and_linked() -> None:
    source = '''spec is "1.0"

contract flow "inner":
  input:
    name is text
  output:
    result is text

flow "inner":
  let name is input.name constant
  return map:
    "result" is name

flow "outer":
  let name is "outer"
  let first is call flow "inner":
    input:
      name is name
    output:
      result
  set name is "updated"
  let second is call flow "inner":
    input:
      name is name
    output:
      result
  return map:
    "first" is map get first key "result"
    "second" is map get second key "result"
'''
    first = run_flow(source, flow_name="outer")
    second = run_flow(source, flow_name="outer")

    assert first.last_value == {"first": "outer", "second": "updated"}
    assert second.last_value == first.last_value

    first_events = _flow_call_events(first)
    second_events = _flow_call_events(second)
    assert first_events == second_events

    assert [event["type"] for event in first_events] == [
        TraceEventType.FLOW_CALL_STARTED,
        TraceEventType.FLOW_CALL_FINISHED,
        TraceEventType.FLOW_CALL_STARTED,
        TraceEventType.FLOW_CALL_FINISHED,
    ]

    ids = [event["flow_call_id"] for event in first_events]
    assert ids == ["flow_call:0001", "flow_call:0001", "flow_call:0002", "flow_call:0002"]

    start_events = [event for event in first_events if event["type"] == TraceEventType.FLOW_CALL_STARTED]
    finish_events = [event for event in first_events if event["type"] == TraceEventType.FLOW_CALL_FINISHED]
    assert [event["flow_call_id"] for event in start_events] == ["flow_call:0001", "flow_call:0002"]
    assert [event["flow_call_id"] for event in finish_events] == ["flow_call:0001", "flow_call:0002"]

    for event in start_events:
        assert event["caller_flow"] == "outer"
        assert event["callee_flow"] == "inner"
        assert event["inputs"] == ["name"]
        assert event["outputs"] == ["result"]

    for event in finish_events:
        assert event["caller_flow"] == "outer"
        assert event["callee_flow"] == "inner"
        assert event["status"] == "ok"


def _store_text_upload(tmp_path: Path, app_path: Path, payload: bytes) -> dict:
    ctx = SimpleNamespace(project_root=str(tmp_path), app_path=app_path.as_posix())
    return store_upload(ctx, filename="notes.txt", content_type="text/plain", stream=io.BytesIO(payload))


def test_pipeline_calls_ingestion_and_retrieval(tmp_path: Path) -> None:
    source = '''spec is "1.0"

capabilities:
  uploads

flow "demo":
  let ingestion_out is call pipeline "ingestion":
    input:
      upload_id is input.upload_id
    output:
      report
      ingestion
      index
  let retrieval_out is call pipeline "retrieval":
    input:
      query is input.query
    output:
      report
  return map:
    "ingestion_call" is ingestion_out
    "retrieval_call" is retrieval_out
'''
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    payload = b"hello world with enough distinct words to pass the deterministic quality gate for retrieval"
    metadata = _store_text_upload(tmp_path, app_path, payload)

    first = run_flow(
        source,
        flow_name="demo",
        input_data={"upload_id": metadata["checksum"], "query": "hello"},
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )
    second = run_flow(
        source,
        flow_name="demo",
        input_data={"upload_id": metadata["checksum"], "query": "hello"},
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )

    assert first.last_value == second.last_value
    assert isinstance(first.last_value, dict)

    output = first.last_value
    ingestion_call = output["ingestion_call"]
    retrieval_call = output["retrieval_call"]
    report = ingestion_call["report"]

    assert report["upload_id"] == metadata["checksum"]
    assert metadata["checksum"] in ingestion_call["ingestion"]
    assert isinstance(ingestion_call["index"].get("chunks"), list)
    assert ingestion_call["index"]["chunks"]

    retrieval_report = retrieval_call["report"]
    assert retrieval_report["results"]
    assert {item["upload_id"] for item in retrieval_report["results"]} == {metadata["checksum"]}
