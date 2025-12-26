# admin-ui

Admin pages, table views, and basic actions for internal tooling.

## Install

```
n3 pkg add github:namel3ss-ai/admin-ui@v0.1.0
```

## Usage

```
use "admin-ui" as admin

page "home":
  button "Seed admin item":
    calls flow "admin.seed_item"
  table is "admin.AdminItem"
```

## Development

```
n3 pkg validate .
n3 test
n3 verify --prod
```
