from __future__ import annotations

from datetime import datetime
from unittest import TestCase

from monitor.alerts import AlertEvaluator
from monitor.models import GpuInfo, SystemSnapshot


class AlertEvaluatorTest(TestCase):
    def test_evaluate_returns_alerts_for_hot_resources_after_sustained_samples(self) -> None:
        first_snapshot = SystemSnapshot(
            timestamp=datetime(2026, 4, 2, 16, 45, 0),
            cpu_percent=95.0,
            per_cpu_percent=[90.0, 92.0],
            memory_percent=88.0,
            disk_percent=91.0,
            net_bytes_sent=100,
            net_bytes_recv=200,
            net_sent_rate=0.0,
            net_recv_rate=0.0,
            net_sent_rate_smoothed=0.0,
            net_recv_rate_smoothed=0.0,
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
        second_snapshot = SystemSnapshot(
            timestamp=datetime(2026, 4, 2, 16, 45, 0),
            cpu_percent=95.0,
            per_cpu_percent=[90.0, 92.0],
            memory_percent=88.0,
            disk_percent=91.0,
            net_bytes_sent=100,
            net_bytes_recv=200,
            net_sent_rate=0.0,
            net_recv_rate=0.0,
            net_sent_rate_smoothed=0.0,
            net_recv_rate_smoothed=0.0,
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

        evaluator = AlertEvaluator(sustain_samples=2, cooldown_seconds=30.0)
        first_alerts = evaluator.evaluate(first_snapshot)
        alerts = evaluator.evaluate(second_snapshot)

        self.assertEqual(first_alerts, [])
        self.assertEqual(len(alerts), 4)
        self.assertIn("High CPU usage: 95.0%", alerts)
        self.assertIn("High memory usage: 88.0%", alerts)
        self.assertIn("High disk usage: 91.0%", alerts)
        self.assertIn("High GPU usage on GPU 0: 97.0%", alerts)

    def test_evaluate_respects_cooldown_for_repeated_alerts(self) -> None:
        evaluator = AlertEvaluator(sustain_samples=1, cooldown_seconds=30.0)
        first_snapshot = SystemSnapshot(
            timestamp=datetime(2026, 4, 2, 16, 45, 0),
            cpu_percent=95.0,
            per_cpu_percent=[95.0],
            memory_percent=50.0,
            disk_percent=50.0,
            net_bytes_sent=100,
            net_bytes_recv=200,
            net_sent_rate=0.0,
            net_recv_rate=0.0,
            net_sent_rate_smoothed=0.0,
            net_recv_rate_smoothed=0.0,
            alerts=[],
            gpu_info=[],
            top_processes=[],
        )
        second_snapshot = SystemSnapshot(
            timestamp=datetime(2026, 4, 2, 16, 45, 10),
            cpu_percent=96.0,
            per_cpu_percent=[96.0],
            memory_percent=50.0,
            disk_percent=50.0,
            net_bytes_sent=100,
            net_bytes_recv=200,
            net_sent_rate=0.0,
            net_recv_rate=0.0,
            net_sent_rate_smoothed=0.0,
            net_recv_rate_smoothed=0.0,
            alerts=[],
            gpu_info=[],
            top_processes=[],
        )
        third_snapshot = SystemSnapshot(
            timestamp=datetime(2026, 4, 2, 16, 45, 31),
            cpu_percent=97.0,
            per_cpu_percent=[97.0],
            memory_percent=50.0,
            disk_percent=50.0,
            net_bytes_sent=100,
            net_bytes_recv=200,
            net_sent_rate=0.0,
            net_recv_rate=0.0,
            net_sent_rate_smoothed=0.0,
            net_recv_rate_smoothed=0.0,
            alerts=[],
            gpu_info=[],
            top_processes=[],
        )

        first_alerts = evaluator.evaluate(first_snapshot)
        second_alerts = evaluator.evaluate(second_snapshot)
        third_alerts = evaluator.evaluate(third_snapshot)

        self.assertEqual(first_alerts, ["High CPU usage: 95.0%"])
        self.assertEqual(second_alerts, [])
        self.assertEqual(third_alerts, ["High CPU usage: 97.0%"])
