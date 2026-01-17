# Jobs and Persistence Demo

Small demo that queues a background job which writes records.

How to use it:
- copy this folder to a new project directory
- enable persistence with sqlite (examples below)
- run `n3 run`
- click "Queue entry"
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
