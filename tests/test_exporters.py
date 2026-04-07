from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import TestCase

from monitor.exporters import (
    CsvSnapshotExporter,
    JsonSnapshotExporter,
    SqliteSnapshotExporter,
    create_exporter,
    load_sqlite_history,
    load_sqlite_latest,
)
from monitor.models import GpuInfo, ProcessInfo, SystemSnapshot


def build_snapshot() -> SystemSnapshot:
    return SystemSnapshot(
        timestamp=datetime(2026, 4, 2, 19, 30, 0),
        cpu_percent=10.0,
        per_cpu_percent=[10.0, 20.0],
        memory_percent=30.0,
        disk_percent=40.0,
        net_bytes_sent=100,
        net_bytes_recv=200,
        net_sent_rate=3.0,
        net_recv_rate=4.0,
        net_sent_rate_smoothed=2.5,
        net_recv_rate_smoothed=3.5,
        alerts=["warning"],
        gpu_info=[GpuInfo(name="GPU 0", utilization_percent=50.0, memory_used_mb=100, memory_total_mb=1000)],
        top_processes=[ProcessInfo(pid=1, name="python", cpu_percent=5.0, memory_percent=1.0)],
    )


class ExporterTest(TestCase):
    def test_json_exporter_writes_one_record_per_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "monitor.jsonl"
            exporter = JsonSnapshotExporter(str(output))
            exporter.write(build_snapshot())
            exporter.close()

            lines = output.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["cpu_percent"], 10.0)
            self.assertEqual(record["timestamp"], "2026-04-02T19:30:00")

    def test_csv_exporter_writes_header_and_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "monitor.csv"
            exporter = CsvSnapshotExporter(str(output))
            exporter.write(build_snapshot())
            exporter.close()

            content = output.read_text(encoding="utf-8")
            self.assertIn("timestamp,cpu_percent,per_cpu_percent", content)
            self.assertIn("2026-04-02T19:30:00", content)
            self.assertIn('"[10.0, 20.0]"', content)

    def test_create_exporter_returns_none_without_path(self) -> None:
        self.assertIsNone(create_exporter(None, "json"))

    def test_create_exporter_passes_sqlite_retention(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "monitor.db"
            exporter = create_exporter(str(output), "sqlite", retention_max_rows=10)

            self.assertIsInstance(exporter, SqliteSnapshotExporter)
            assert exporter is not None
            self.assertEqual(exporter.retention_max_rows, 10)
            exporter.close()

    def test_sqlite_exporter_inserts_snapshot_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "monitor.db"
            exporter = SqliteSnapshotExporter(str(output))
            exporter.write(build_snapshot())
            exporter.close()

            connection = sqlite3.connect(output)
            row = connection.execute(
                "SELECT timestamp, cpu_percent, net_sent_rate_smoothed, alerts FROM snapshots"
            ).fetchone()
            connection.close()

            self.assertEqual(row[0], "2026-04-02T19:30:00")
            self.assertEqual(row[1], 10.0)
            self.assertEqual(row[2], 2.5)
            self.assertEqual(row[3], '["warning"]')

    def test_sqlite_loader_reads_latest_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "monitor.db"
            exporter = SqliteSnapshotExporter(str(output))
            first = build_snapshot()
            second = build_snapshot()
            second.cpu_percent = 20.0
            second.timestamp = datetime(2026, 4, 2, 19, 31, 0)
            exporter.write(first)
            exporter.write(second)
            exporter.close()

            latest = load_sqlite_latest(str(output))
            history = load_sqlite_history(str(output), 2)

            self.assertIsNotNone(latest)
            self.assertEqual(latest.cpu_percent, 20.0)
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0].cpu_percent, 10.0)
            self.assertEqual(history[1].cpu_percent, 20.0)

    def test_sqlite_loader_supports_since_and_before_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "monitor.db"
            exporter = SqliteSnapshotExporter(str(output))
            first = build_snapshot()
            second = build_snapshot()
            third = build_snapshot()
            second.timestamp = datetime(2026, 4, 2, 19, 31, 0)
            second.cpu_percent = 20.0
            third.timestamp = datetime(2026, 4, 2, 19, 32, 0)
            third.cpu_percent = 30.0
            exporter.write(first)
            exporter.write(second)
            exporter.write(third)
            exporter.close()

            history = load_sqlite_history(
                str(output),
                limit=5,
                since="2026-04-02T19:31:00",
                before="2026-04-02T19:32:00",
            )
            latest = load_sqlite_latest(
                str(output),
                since="2026-04-02T19:31:00",
                before="2026-04-02T19:32:00",
            )

            self.assertEqual(len(history), 2)
            self.assertEqual(history[0].cpu_percent, 20.0)
            self.assertEqual(history[1].cpu_percent, 30.0)
            self.assertIsNotNone(latest)
            self.assertEqual(latest.cpu_percent, 30.0)

    def test_sqlite_exporter_prunes_old_rows_when_retention_is_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "monitor.db"
            exporter = SqliteSnapshotExporter(str(output), retention_max_rows=2)
            first = build_snapshot()
            second = build_snapshot()
            third = build_snapshot()
            second.timestamp = datetime(2026, 4, 2, 19, 31, 0)
            second.cpu_percent = 20.0
            third.timestamp = datetime(2026, 4, 2, 19, 32, 0)
            third.cpu_percent = 30.0
            exporter.write(first)
            exporter.write(second)
            exporter.write(third)
            exporter.close()

            history = load_sqlite_history(str(output), 10)

            self.assertEqual(len(history), 2)
            self.assertEqual(history[0].cpu_percent, 20.0)
            self.assertEqual(history[1].cpu_percent, 30.0)
