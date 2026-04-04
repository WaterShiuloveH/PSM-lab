from __future__ import annotations

import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from monitor.exporters import snapshot_to_record
from monitor.models import SystemSnapshot


def create_api_server(
    host: str,
    port: int,
    latest_snapshot_provider,
    history_provider,
) -> ThreadingHTTPServer:
    class MonitorRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            status, payload = build_api_response(
                self.path,
                latest_snapshot_provider=latest_snapshot_provider,
                history_provider=history_provider,
            )
            self._write_json(payload, status=status)

        def log_message(self, format: str, *args) -> None:
            return None

        def _write_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((host, port), MonitorRequestHandler)


def build_api_response(
    path: str,
    latest_snapshot_provider,
    history_provider,
) -> tuple[HTTPStatus, dict[str, object]]:
    parsed = urlparse(path)

    if parsed.path == "/health":
        return HTTPStatus.OK, {"status": "ok"}

    if parsed.path == "/api/latest":
        snapshot = latest_snapshot_provider()
        if snapshot is None:
            return HTTPStatus.OK, {"snapshot": None}
        return HTTPStatus.OK, {"snapshot": snapshot_to_record(snapshot)}

    if parsed.path == "/api/history":
        params = parse_qs(parsed.query)
        limit = _parse_limit(params.get("limit", ["10"])[0], default=10)
        history = history_provider(limit)
        return HTTPStatus.OK, {
            "snapshots": [snapshot_to_record(snapshot) for snapshot in history]
        }

    return HTTPStatus.NOT_FOUND, {"error": "not_found"}


class ApiServerHandle:
    def __init__(self, server: ThreadingHTTPServer) -> None:
        self._server = server
        self._thread = threading.Thread(target=server.serve_forever, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2.0)


def _parse_limit(value: str, default: int) -> int:
    try:
        return max(int(value), 1)
    except ValueError:
        return default
