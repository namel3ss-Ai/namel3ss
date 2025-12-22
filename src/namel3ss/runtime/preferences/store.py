from __future__ import annotations

from pathlib import Path
from typing import Optional

ALLOWED_THEMES = {"light", "dark", "system"}


class PreferenceStore:
    def load_theme(self, app_key: str) -> tuple[Optional[str], Optional[str]]:
        raise NotImplementedError

    def save_theme(self, app_key: str, value: str) -> None:
        raise NotImplementedError


class NoopPreferenceStore(PreferenceStore):
    def load_theme(self, app_key: str) -> tuple[Optional[str], Optional[str]]:  # pragma: no cover - trivial
        return None, None

    def save_theme(self, app_key: str, value: str) -> None:  # pragma: no cover - trivial
        return None


class FilePreferenceStore(PreferenceStore):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            import json

            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"corrupt": True}

    def _write_atomic(self, data: dict) -> None:
        import json
        import os
        from tempfile import NamedTemporaryFile

        with NamedTemporaryFile("w", delete=False, dir=str(self.path.parent), encoding="utf-8") as tmp:
            json.dump(data, tmp)
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, self.path)

    def load_theme(self, app_key: str) -> tuple[Optional[str], Optional[str]]:
        data = self._read()
        if data.get("corrupt"):
            return None, "Preference file could not be read; ignoring stored theme."
        themes = data.get("themes", {})
        value = themes.get(app_key)
        if value in ALLOWED_THEMES:
            return value, None
        return None, None

    def save_theme(self, app_key: str, value: str) -> None:
        if value not in ALLOWED_THEMES:
            return
        data = self._read()
        themes = data.get("themes", {})
        themes[app_key] = value
        data["themes"] = themes
        self._write_atomic(data)
