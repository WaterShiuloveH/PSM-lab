from __future__ import annotations

from datetime import datetime
from unittest import TestCase

from monitor.models import SystemSnapshot
from monitor.sampler import SystemSampler


class SystemSamplerTrendTest(TestCase):
    def test_summarize_recent_trends_returns_ascii_summaries(self) -> None:
        sampler = SystemSampler(history_size=5)
        sampler.history.extend(
            [
                SystemSnapshot(
                    timestamp=datetime(2026, 4, 2, 18, 0, second),
                    cpu_percent=float(second),
                    per_cpu_percent=[float(second)],
                    memory_percent=float(second * 2),
                    disk_percent=7.0,
                    net_bytes_sent=100,
                    net_bytes_recv=200,
                    net_sent_rate=float(second * 10),
                    net_recv_rate=float(second * 20),
                    net_sent_rate_smoothed=float(second * 10),
                    net_recv_rate_smoothed=float(second * 20),
                    alerts=[],
                    gpu_info=[],
                    top_processes=[],
                )
                for second in range(1, 5)
            ]
        )

        trends = sampler.summarize_recent_trends(points=4)

        self.assertEqual(set(trends.keys()), {"cpu", "memory", "network_up", "network_down"})
        self.assertEqual(len(trends["cpu"]), 4)
        self.assertNotEqual(trends["cpu"], "n/a")
        self.assertTrue(all(char in "▁▂▃▄▅▆▇█" for char in trends["cpu"]))
