# Smoke Demo

One-button app that proves UI -> action -> state in the browser.

How to use it:
- copy this folder to a new project directory
- run `n3 check` from the copied folder
- run `n3 run` and open the browser
- click "Add click" to create a record and watch the table update
- identity defaults in `namel3ss.toml` enable the permission guard and Studio traces
- run `n3 pack --target service` to build deterministic artifacts
- run `n3 ship --to service` to promote the build
- open Studio to review Deploy, Logs, Tracing, and Metrics for the run
