# data/

This folder is a host mount for Docker runtime artifacts written to `.namel3ss/`
(e.g., the SQLite database and other local runtime state).

It exists so fresh-clone `docker compose up --build` works reliably on Linux
without Docker creating a root-owned `./data` directory.

It is safe to delete to reset local state (when not using Postgres).
Do not commit contents other than this README and `.gitkeep`.
Do not store secrets here.
