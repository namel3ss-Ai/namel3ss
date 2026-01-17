# Application Data Model

The Application Data Model is the language-level contract for how namel3ss apps define structured records and how those records are created, read, updated, deleted, and persisted. It is explicit, deterministic, and part of every `.ai` program.

## What the Data Model covers
- **Records**: typed fields, constraints, and optional tenant scoping or retention.
- **CRUD operations**: create, read, update, delete, and save against declared record schemas.
- **Persistence**: local-first storage with deterministic ordering and a runtime-only default location.
- **Ordering**: stable read order by record id; updates and deletes apply in a deterministic order.
- **Inspection**: Studio can show current state, record collections, and data effects from actions.

## Declaring records
```ai
record "Order":
  fields:
    id is number must be present
    status is text must be present
    total is number must be at least 0
  tenant_key is identity.organization_id
```
- Use `record "Name":` to declare the schema.
- Fields are typed (`text`, `number`, `boolean`, `json`) and can include constraints (`present`, `unique`, `pattern`, `greater than`).
- `tenant_key` scopes records to an identity field.
- `persisted` settings (like `ttl_hours`) are optional; `ttl_hours` uses runtime time to compute retention windows.

## CRUD operations in flows
```ai
flow "create_order": requires true
  set state.order with:
    id is 101
    status is "new"
    total is 19.95
  create "Order" with state.order as order
  return order
```
- `save` stores the current `state.<record>` dictionary.
- `create` inserts a new record from a values dictionary.
- `find` reads records with a predicate and binds `<record>_results`.
- `update` modifies matching records with a `set:` block.
- `delete` removes matching records.

```ai
flow "clean_orders": requires true
  update "Order" where status is "new" set:
    status is "paid"
  delete "Order" where status is "cancelled"
  find "Order" where status is "paid"
  return order_results
```

## Record identity and ordering
- Records use `id` if declared; otherwise `_id` is assigned by the store.
- If you omit an id, the store assigns the next numeric id in insertion order.
- Reads are ordered by id ascending; updates and deletes apply in the same order.
- `find` returns results in deterministic order.
- `latest "Record"` uses the same ordering rules.

## Persistence (local-first)
- Default storage is in-memory and reset on restart.
- Enable persistence with a deterministic local store:

`namel3ss.toml`:
```toml
[persistence]
target = "sqlite"
db_path = ".namel3ss/data.db"
```

Environment:
```bash
N3_PERSIST_TARGET=sqlite
```

The default storage location lives under `.namel3ss/` and is ignored by git.

## Studio inspection
- Studio shows record collections and state in the Data panel.
- Action runs record deterministic data effects (create/update/delete) for review.
- `/api/state` returns the state snapshot plus record collections in stable order.

## Related references
- Application UI Model: `docs/language/application-ui-model.md`.
- Browser Protocol: `docs/runtime/browser-protocol.md`.
- UI DSL: `docs/ui-dsl.md`.
