from __future__ import annotations

import json
from http import HTTPStatus
from datetime import datetime
from unittest import TestCase

from monitor.api import build_api_response
from monitor.models import SystemSnapshot


def build_snapshot(second: int) -> SystemSnapshot:
    return SystemSnapshot(
        timestamp=datetime(2026, 4, 4, 22, 40, second),
        cpu_percent=float(second),
        per_cpu_percent=[float(second)],
        memory_percent=20.0,
        disk_percent=30.0,
        net_bytes_sent=100,
        net_bytes_recv=200,
        net_sent_rate=1.0,
        net_recv_rate=2.0,
        net_sent_rate_smoothed=1.5,
        net_recv_rate_smoothed=2.5,
        alerts=[],
        gpu_info=[],
        top_processes=[],
    )


class ApiServerTest(TestCase):
    def test_api_exposes_health_latest_and_history(self) -> None:
        history = [build_snapshot(1), build_snapshot(2), build_snapshot(3)]
        health_status, health_payload = build_api_response(
            "/health",
            latest_snapshot_provider=lambda **kwargs: history[-1],
            history_provider=lambda **kwargs: history[-kwargs["limit"] :],
        )
        latest_status, latest_payload = build_api_response(
            "/api/latest",
            latest_snapshot_provider=lambda **kwargs: history[-1],
            history_provider=lambda **kwargs: history[-kwargs["limit"] :],
        )
        history_status, history_payload = build_api_response(
            "/api/history?limit=2",
            latest_snapshot_provider=lambda **kwargs: history[-1],
            history_provider=lambda **kwargs: history[-kwargs["limit"] :],
        )
        summary_status, summary_payload = build_api_response(
            "/api/summary?limit=2",
            latest_snapshot_provider=lambda **kwargs: history[-1],
            history_provider=lambda **kwargs: history[-kwargs["limit"] :],
            storage_metadata_provider=lambda: {"backend": "memory", "memory_history_size": 3},
        )

        self.assertEqual(health_status, HTTPStatus.OK)
        self.assertEqual(health_payload["status"], "ok")
        self.assertEqual(latest_status, HTTPStatus.OK)
        self.assertEqual(latest_payload["snapshot"]["timestamp"], "2026-04-04T22:40:03")
        self.assertEqual(history_status, HTTPStatus.OK)
        self.assertEqual(len(history_payload["snapshots"]), 2)
        self.assertEqual(history_payload["snapshots"][0]["timestamp"], "2026-04-04T22:40:02")
        self.assertEqual(summary_status, HTTPStatus.OK)
        self.assertEqual(summary_payload["summary"]["samples"], 2)
        self.assertEqual(summary_payload["summary"]["latest"]["timestamp"], "2026-04-04T22:40:03")
        self.assertEqual(summary_payload["summary"]["storage"]["backend"], "memory")

    def test_api_returns_not_found_for_unknown_path(self) -> None:
        status, payload = build_api_response(
            "/missing",
            latest_snapshot_provider=lambda **kwargs: None,
            history_provider=lambda **kwargs: [],
        )

        self.assertEqual(status, HTTPStatus.NOT_FOUND)
        self.assertEqual(payload["error"], "not_found")

    def test_api_exposes_recent_alerts(self) -> None:
        history = [build_snapshot(1), build_snapshot(2), build_snapshot(3)]
        history[1].alerts = ["High CPU usage: 95.0%"]
        history[2].alerts = ["High memory usage: 90.0%"]

        status, payload = build_api_response(
            "/api/alerts?limit=3",
            latest_snapshot_provider=lambda **kwargs: history[-1],
            history_provider=lambda **kwargs: history[-kwargs["limit"] :],
        )

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(len(payload["alerts"]), 2)
        self.assertEqual(payload["alerts"][0]["message"], "High CPU usage: 95.0%")
        self.assertEqual(payload["alerts"][1]["message"], "High memory usage: 90.0%")

    def test_api_supports_since_and_before_filters(self) -> None:
        history = [build_snapshot(1), build_snapshot(2), build_snapshot(3)]

        def latest_provider(**kwargs):
            filtered = history_provider(**kwargs)
            return filtered[-1] if filtered else None

        def history_provider(**kwargs):
            snapshots = history
            since = kwargs.get("since")
            before = kwargs.get("before")
            if since is not None:
                snapshots = [snapshot for snapshot in snapshots if snapshot.timestamp.isoformat() >= since]
            if before is not None:
                snapshots = [snapshot for snapshot in snapshots if snapshot.timestamp.isoformat() <= before]
            return snapshots[-kwargs["limit"] :]

        status, payload = build_api_response(
            "/api/history?limit=5&since=2026-04-04T22:40:02&before=2026-04-04T22:40:03",
            latest_snapshot_provider=latest_provider,
            history_provider=history_provider,
        )

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(len(payload["snapshots"]), 2)
        self.assertEqual(payload["snapshots"][0]["timestamp"], "2026-04-04T22:40:02")
        self.assertEqual(payload["snapshots"][1]["timestamp"], "2026-04-04T22:40:03")

    def test_summary_includes_storage_metadata_when_available(self) -> None:
        history = [build_snapshot(1), build_snapshot(2)]

        status, payload = build_api_response(
            "/api/summary?limit=2",
            latest_snapshot_provider=lambda **kwargs: history[-1],
            history_provider=lambda **kwargs: history[-kwargs["limit"] :],
            storage_metadata_provider=lambda: {
                "backend": "sqlite",
                "path": "snapshots.db",
                "row_count": 42,
                "retention_max_rows": 500,
                "memory_history_size": 2,
            },
        )

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload["summary"]["storage"]["backend"], "sqlite")
        self.assertEqual(payload["summary"]["storage"]["row_count"], 42)
        self.assertEqual(payload["summary"]["storage"]["retention_max_rows"], 500)
