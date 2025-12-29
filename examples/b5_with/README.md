# b5_with

This example shows the tool gate and tool proof pack.

Run:
- `cd examples/b5_with`
- `n3 run app.ai flow "demo"`
- `n3 with`

Notes:
- The flow stops on the blocked tool (no binding), so the run fails.
- The tool report still records allowed and blocked calls.

Artifacts live under `.namel3ss/tools/`.
