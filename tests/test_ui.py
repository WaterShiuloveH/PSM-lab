from __future__ import annotations

from datetime import datetime
from unittest import TestCase

from monitor.models import GpuInfo, ProcessInfo, SystemSnapshot
from monitor.ui import render_snapshot


class RenderSnapshotTest(TestCase):
    def test_render_snapshot_includes_main_fields_and_processes(self) -> None:
        snapshot = SystemSnapshot(
            timestamp=datetime(2026, 4, 2, 16, 30, 0),
            cpu_percent=55.5,
            per_cpu_percent=[55.0, 56.0, 40.0],
            memory_percent=80.0,
            disk_percent=6.9,
            net_bytes_sent=1234,
            net_bytes_recv=5678,
            net_sent_rate=2048.0,
            net_recv_rate=512.0,
            net_sent_rate_smoothed=1024.0,
            net_recv_rate_smoothed=256.0,
            alerts=["High memory usage: 80.0%"],
            gpu_info=[
                GpuInfo(
                    name="GPU 0",
                    utilization_percent=75.0,
                    memory_used_mb=800,
                    memory_total_mb=16000,
                )
            ],
            top_processes=[
                ProcessInfo(pid=42, name="python", cpu_percent=22.0, memory_percent=3.5)
            ],
        )

        rendered = render_snapshot(snapshot)

        self.assertIn("Time: 2026-04-02 16:30:00", rendered)
        self.assertIn("CPU:", rendered)
        self.assertIn("Memory:", rendered)
        self.assertIn("Disk:", rendered)
        self.assertIn("Net Up:", rendered)
        self.assertIn("1.00 KB/s", rendered)
        self.assertIn("2.00 KB/s", rendered)
        self.assertIn("Net Down:", rendered)
        self.assertIn("256.00 B/s", rendered)
        self.assertIn("512.00 B/s", rendered)
        self.assertIn("Net Up Raw:", rendered)
        self.assertIn("Net Down Raw:", rendered)
        self.assertIn("Net Sent Total: 1234 bytes", rendered)
        self.assertIn("Net Recv Total: 5678 bytes", rendered)
        self.assertIn("Recent Trends:", rendered)
        self.assertIn("Legend: low -> high | ▁▂▃▄▅▆▇█", rendered)
        self.assertIn("Per-Core:", rendered)
        self.assertIn("c0:", rendered)
        self.assertIn("Alerts:", rendered)
        self.assertIn("High memory usage: 80.0%", rendered)
        self.assertIn("GPUs:", rendered)
        self.assertIn("GPU 0", rendered)
        self.assertIn("Top Processes:", rendered)
        self.assertIn("PID=42", rendered)
        self.assertIn("python", rendered)

    def test_render_snapshot_includes_custom_trends(self) -> None:
        snapshot = SystemSnapshot(
            timestamp=datetime(2026, 4, 2, 16, 30, 0),
            cpu_percent=10.0,
            per_cpu_percent=[10.0],
            memory_percent=20.0,
            disk_percent=30.0,
            net_bytes_sent=100,
            net_bytes_recv=200,
            net_sent_rate=10.0,
            net_recv_rate=20.0,
            net_sent_rate_smoothed=8.0,
            net_recv_rate_smoothed=16.0,
            alerts=[],
            gpu_info=[],
            top_processes=[],
        )

        rendered = render_snapshot(
            snapshot,
            trends={
                "cpu": "▁▃▆█",
                "memory": "▂▂▅▅",
                "network_up": "▁▁▃▅",
                "network_down": "▁▄▆█",
            },
        )

        self.assertIn("CPU:      ▁▃▆█", rendered)
        self.assertIn("Memory:   ▂▂▅▅", rendered)
        self.assertIn("Net Up:   ▁▁▃▅", rendered)
        self.assertIn("Net Down: ▁▄▆█", rendered)
