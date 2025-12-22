from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.preferences.store import FilePreferenceStore, NoopPreferenceStore, PreferenceStore


def preference_store_for_app(app_path: str | None, persist_mode: str | None) -> PreferenceStore:
    if persist_mode != "file" or not app_path:
        return NoopPreferenceStore()
    base = Path(app_path).resolve().parent / ".namel3ss"
    return FilePreferenceStore(base / "preferences.json")


def app_pref_key(app_path: str | None) -> str:
    if not app_path:
        return ""
    return str(Path(app_path).resolve())
