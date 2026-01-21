# Persistence Demo

Small demo that writes records and reads them back with persistence enabled.

How to use it:
- copy this folder to a new project directory
- enable persistence with sqlite (examples below)
- run `n3 run`
- open `n3 app.ai studio` and inspect the Data panel for backend target and migration status
- add an entry
- stop and run again; entries remain when persistence is enabled

Config example (`namel3ss.toml`):
```toml
[persistence]
target = "sqlite"
db_path = ".namel3ss/data.db"
```

Environment example:
```bash
N3_PERSIST_TARGET=sqlite
```
