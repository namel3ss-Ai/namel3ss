# record_roundtrip

This example shows deterministic run outcome packs.

Run (ok outcome):
- `cd examples/record_roundtrip`
- `n3 run app.ai`
- `n3 what`

Optional partial outcome (force memory persistence failure):
- `cd examples/record_roundtrip`
- `mkdir -p .namel3ss`
- `chmod -w .namel3ss`
- `n3 run app.ai`
- `n3 what`
- `chmod +w .namel3ss`

Artifacts live under `.namel3ss/outcome/`.
