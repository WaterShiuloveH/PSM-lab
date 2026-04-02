from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from unittest.mock import Mock
from unittest.mock import patch

from monitor.models import GpuInfo, ProcessInfo, SystemSnapshot
from monitor.sampler import SystemSampler


class SystemSamplerTest(TestCase):
    @patch("monitor.sampler.collect_gpu_info")
    @patch("monitor.sampler.collect_top_processes")
    @patch("monitor.sampler.collect_network_counters")
    @patch("monitor.sampler.collect_disk_percent")
    @patch("monitor.sampler.collect_memory_percent")
    @patch("monitor.sampler.collect_per_cpu_percent")
    @patch("monitor.sampler.collect_cpu_percent")
    def test_sample_builds_snapshot_and_appends_history(
        self,
        mock_cpu_percent,
        mock_per_cpu_percent,
        mock_memory_percent,
        mock_disk_percent,
        mock_network_counters,
        mock_collect_top_processes,
        mock_collect_gpu_info,
    ) -> None:
        mock_cpu_percent.return_value = 12.5
        mock_per_cpu_percent.return_value = [10.0, 15.0]
        mock_memory_percent.return_value = 68.0
        mock_disk_percent.return_value = 40.0
        mock_network_counters.return_value = (1000, 2000)
        mock_collect_top_processes.return_value = [
            ProcessInfo(pid=1, name="python", cpu_percent=3.5, memory_percent=0.8)
        ]
        mock_collect_gpu_info.return_value = [
            GpuInfo(
                name="GPU 0",
                utilization_percent=20.0,
                memory_used_mb=500,
                memory_total_mb=16000,
            )
        ]

        sampler = SystemSampler(history_size=2)
        snapshot = sampler.sample()

        self.assertIsInstance(snapshot, SystemSnapshot)
        self.assertIsInstance(snapshot.timestamp, datetime)
        self.assertEqual(snapshot.cpu_percent, 12.5)
        self.assertEqual(snapshot.per_cpu_percent, [10.0, 15.0])
        self.assertEqual(snapshot.memory_percent, 68.0)
        self.assertEqual(snapshot.disk_percent, 40.0)
        self.assertEqual(snapshot.net_bytes_sent, 1000)
        self.assertEqual(snapshot.net_bytes_recv, 2000)
        self.assertEqual(snapshot.net_sent_rate, 0.0)
        self.assertEqual(snapshot.net_recv_rate, 0.0)
        self.assertEqual(len(snapshot.gpu_info), 1)
        self.assertEqual(len(snapshot.top_processes), 1)
        self.assertEqual(len(sampler.history), 1)
        self.assertIs(sampler.history[-1], snapshot)

    @patch("monitor.sampler.collect_gpu_info", return_value=[])
    @patch("monitor.sampler.collect_top_processes", return_value=[])
    @patch("monitor.sampler.collect_network_counters", return_value=(1, 2))
    @patch("monitor.sampler.collect_disk_percent", return_value=3.0)
    @patch("monitor.sampler.collect_memory_percent", return_value=4.0)
    @patch("monitor.sampler.collect_per_cpu_percent", return_value=[6.0, 7.0])
    @patch("monitor.sampler.collect_cpu_percent", return_value=5.0)
    def test_history_respects_max_length(
        self,
        mock_cpu_percent,
        mock_per_cpu_percent,
        mock_memory_percent,
        mock_disk_percent,
        mock_network_counters,
        mock_collect_top_processes,
        mock_collect_gpu_info,
    ) -> None:
        sampler = SystemSampler(history_size=2)

        sampler.sample()
        sampler.sample()
        sampler.sample()

        self.assertEqual(len(sampler.history), 2)

    @patch("monitor.sampler.collect_gpu_info", return_value=[])
    @patch("monitor.sampler.collect_top_processes", return_value=[])
    @patch("monitor.sampler.collect_network_counters", return_value=(1, 2))
    @patch("monitor.sampler.collect_disk_percent", return_value=3.0)
    @patch("monitor.sampler.collect_memory_percent", return_value=96.0)
    @patch("monitor.sampler.collect_per_cpu_percent", return_value=[96.0, 95.0])
    @patch("monitor.sampler.collect_cpu_percent", return_value=95.0)
    def test_sample_applies_alert_evaluator(
        self,
        mock_cpu_percent,
        mock_per_cpu_percent,
        mock_memory_percent,
        mock_disk_percent,
        mock_network_counters,
        mock_collect_top_processes,
        mock_collect_gpu_info,
    ) -> None:
        alert_evaluator = Mock()
        alert_evaluator.evaluate.return_value = ["High CPU usage: 95.0%"]

        sampler = SystemSampler(history_size=2, alert_evaluator=alert_evaluator)
        snapshot = sampler.sample()

        alert_evaluator.evaluate.assert_called_once()
        self.assertEqual(snapshot.alerts, ["High CPU usage: 95.0%"])

    @patch("monitor.sampler.collect_gpu_info", return_value=[])
    @patch("monitor.sampler.collect_top_processes", return_value=[])
    @patch("monitor.sampler.collect_network_counters", side_effect=[(100, 200), (160, 320)])
    @patch("monitor.sampler.collect_disk_percent", return_value=3.0)
    @patch("monitor.sampler.collect_memory_percent", return_value=4.0)
    @patch("monitor.sampler.collect_per_cpu_percent", return_value=[6.0, 7.0])
    @patch("monitor.sampler.collect_cpu_percent", return_value=5.0)
    @patch("monitor.sampler.datetime")
    def test_sample_computes_network_throughput_from_previous_sample(
        self,
        mock_datetime,
        mock_cpu_percent,
        mock_per_cpu_percent,
        mock_memory_percent,
        mock_disk_percent,
        mock_network_counters,
        mock_collect_top_processes,
        mock_collect_gpu_info,
    ) -> None:
        mock_datetime.now.side_effect = [
            datetime(2026, 4, 2, 17, 0, 0),
            datetime(2026, 4, 2, 17, 0, 2),
        ]

        sampler = SystemSampler(history_size=2)
        first_snapshot = sampler.sample()
        second_snapshot = sampler.sample()

        self.assertEqual(first_snapshot.net_sent_rate, 0.0)
        self.assertEqual(first_snapshot.net_recv_rate, 0.0)
        self.assertEqual(second_snapshot.net_sent_rate, 30.0)
        self.assertEqual(second_snapshot.net_recv_rate, 60.0)
