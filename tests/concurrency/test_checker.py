from __future__ import annotations

from namel3ss.concurrency import run_concurrency_checks


def test_concurrency_checker_reports_parallel_writes_and_bad_await() -> None:
    source = '''spec is "1.0"

flow "bad":
  await missing_task
  parallel:
    run "one":
      set state.total is 1
'''
    report = run_concurrency_checks(source)
    assert report["ok"] is False
    assert int(report["count"]) >= 2
    reasons = [item.get("reason", "") for item in report.get("violations", [])]
    assert any("await" in reason for reason in reasons)
    assert any("parallel block changes shared state" in reason for reason in reasons)


def test_concurrency_checker_accepts_valid_async_pattern() -> None:
    source = '''spec is "1.0"

define function "calc":
  input:
    value is number
  output:
    total is number
  return map:
    "total" is value + 1

flow "ok":
  let task is async call function "calc":
    value is 2
  await task
  return task.total
'''
    report = run_concurrency_checks(source)
    assert report["ok"] is True
    assert report["count"] == 0
