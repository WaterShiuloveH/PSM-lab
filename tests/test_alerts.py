from __future__ import annotations

from datetime import datetime
from unittest import TestCase

from monitor.alerts import AlertEvaluator
from monitor.models import GpuInfo, SystemSnapshot


class AlertEvaluatorTest(TestCase):
    def test_evaluate_returns_alerts_for_hot_resources(self) -> None:
        snapshot = SystemSnapshot(
            timestamp=datetime(2026, 4, 2, 16, 45, 0),
            cpu_percent=95.0,
            per_cpu_percent=[90.0, 92.0],
            memory_percent=88.0,
            disk_percent=91.0,
            net_bytes_sent=100,
            net_bytes_recv=200,
            net_sent_rate=0.0,
            net_recv_rate=0.0,
            alerts=[],
            gpu_info=[
                GpuInfo(
                    name="GPU 0",
                    utilization_percent=97.0,
                    memory_used_mb=1000,
                    memory_total_mb=12000,
                )
            ],
            top_processes=[],
        )

        alerts = AlertEvaluator().evaluate(snapshot)

        self.assertEqual(len(alerts), 4)
        self.assertIn("High CPU usage: 95.0%", alerts)
        self.assertIn("High memory usage: 88.0%", alerts)
        self.assertIn("High disk usage: 91.0%", alerts)
        self.assertIn("High GPU usage on GPU 0: 97.0%", alerts)
