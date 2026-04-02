from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import TestCase

from monitor.exporters import CsvSnapshotExporter, JsonSnapshotExporter, create_exporter
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
