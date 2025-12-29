# b3_what

This example shows deterministic run outcome packs.

Run (ok outcome):
- `cd examples/b3_what`
- `n3 run app.ai`
- `n3 what`

Optional partial outcome (force memory persistence failure):
- `cd examples/b3_what`
- `mkdir -p .namel3ss`
- `chmod -w .namel3ss`
- `n3 run app.ai`
- `n3 what`
- `chmod +w .namel3ss`

Artifacts live under `.namel3ss/outcome/`.
