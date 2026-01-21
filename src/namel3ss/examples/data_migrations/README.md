# Data Migrations Example

This example shows how deterministic migrations track record schema changes.

How to use it:
- copy this folder to a new project directory
- set `N3_PERSIST_TARGET=sqlite`
- run `n3 migrate apply app.ai` to establish a baseline
- update `app.ai` to add a field and a record, for example:
  - add `field "name" is text` to `Contact`
  - add a `record "Team"` block with `field "id"` and `field "label"`
- run `n3 migrate plan app.ai` to see the schema changes
- run `n3 migrate status app.ai` to confirm pending migrations
- run `n3 migrate apply app.ai` to apply the plan

Optional:
- run `n3 pack --target service`
- run `n3 ship --to service` to see pending migration guidance
