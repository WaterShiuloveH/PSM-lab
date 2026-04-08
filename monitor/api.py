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
    storage_metadata_provider=None,
) -> ThreadingHTTPServer:
    class MonitorRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            status, payload = build_api_response(
                self.path,
                latest_snapshot_provider=latest_snapshot_provider,
                history_provider=history_provider,
                storage_metadata_provider=storage_metadata_provider,
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
    storage_metadata_provider=None,
) -> tuple[HTTPStatus, dict[str, object]]:
    parsed = urlparse(path)
    params = parse_qs(parsed.query)
    limit = _parse_limit(params.get("limit", ["10"])[0], default=10)
    since = params.get("since", [None])[0]
    before = params.get("before", [None])[0]

    if parsed.path == "/health":
        return HTTPStatus.OK, {"status": "ok"}

    if parsed.path == "/api/latest":
        snapshot = latest_snapshot_provider(since=since, before=before)
        if snapshot is None:
            return HTTPStatus.OK, {"snapshot": None}
        return HTTPStatus.OK, {"snapshot": snapshot_to_record(snapshot)}

    if parsed.path == "/api/history":
        history = history_provider(limit=limit, since=since, before=before)
        return HTTPStatus.OK, {
            "snapshots": [snapshot_to_record(snapshot) for snapshot in history]
        }

    if parsed.path == "/api/summary":
        history = history_provider(limit=limit, since=since, before=before)
        latest = latest_snapshot_provider(since=since, before=before)
        metadata = {}
        if storage_metadata_provider is not None:
            metadata = storage_metadata_provider()
        return HTTPStatus.OK, {"summary": build_summary_payload(history, latest, metadata)}

    if parsed.path == "/api/alerts":
        history = history_provider(limit=limit, since=since, before=before)
        return HTTPStatus.OK, {"alerts": build_alerts_payload(history)}

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


def build_summary_payload(
    history: list[SystemSnapshot],
    latest: SystemSnapshot | None,
    storage: dict[str, object] | None = None,
) -> dict[str, object]:
    if not history:
        return {
            "samples": 0,
            "latest": None,
            "avg_cpu_percent": 0.0,
            "avg_memory_percent": 0.0,
            "avg_net_up": 0.0,
            "avg_net_down": 0.0,
            "storage": storage or {},
        }

    return {
        "samples": len(history),
        "latest": snapshot_to_record(latest) if latest is not None else None,
        "avg_cpu_percent": _average([snapshot.cpu_percent for snapshot in history]),
        "avg_memory_percent": _average([snapshot.memory_percent for snapshot in history]),
        "avg_net_up": _average([snapshot.net_sent_rate_smoothed for snapshot in history]),
        "avg_net_down": _average([snapshot.net_recv_rate_smoothed for snapshot in history]),
        "storage": storage or {},
    }


def build_alerts_payload(history: list[SystemSnapshot]) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for snapshot in history:
        for message in snapshot.alerts:
            payload.append(
                {
                    "timestamp": snapshot.timestamp.isoformat(),
                    "message": message,
                }
            )
    return payload


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
