from __future__ import annotations

from urllib.parse import urlparse

from namel3ss.runtime.server.headless_state_api import (
    handle_stateful_headless_get,
    handle_stateful_headless_options,
    handle_stateful_headless_post,
)
from namel3ss.runtime.server.plugin_assets import (
    plugin_asset_headers,
    request_etag_matches as plugin_request_etag_matches,
    resolve_plugin_asset,
)
from namel3ss.runtime.server.prod.routes import ProductionRequestHandler


class HeadlessProductionRequestHandler(ProductionRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        raw_path = self.path
        path = urlparse(raw_path).path
        if handle_stateful_headless_get(self, path=path, body_path=raw_path):
            return
        if path.startswith("/api/plugins/"):
            state = self._state()
            state._refresh_if_needed()
            asset = resolve_plugin_asset(state.program, path)
            if asset is None:
                self.send_error(404)
                return
            payload, content_type = asset
            headers = plugin_asset_headers(payload)
            if plugin_request_etag_matches(dict(self.headers.items()), headers["ETag"]):
                self.send_response(304)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                return
            self._respond_bytes(payload, status=200, content_type=content_type, headers=headers)
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/api/v"):
            body = self._read_json_body()
            if handle_stateful_headless_post(self, path=path, body=body):
                return
        super().do_POST()

    def do_OPTIONS(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if handle_stateful_headless_options(self, path=path):
            return
        self.send_error(404)


__all__ = ["HeadlessProductionRequestHandler"]
