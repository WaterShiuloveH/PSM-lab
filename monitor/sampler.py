from __future__ import annotations

from collections import deque
from datetime import datetime

from monitor.alerts import AlertEvaluator
from monitor.collectors import (
    collect_cpu_percent,
    collect_disk_percent,
    collect_gpu_info,
    collect_memory_percent,
    collect_network_counters,
    collect_per_cpu_percent,
    collect_top_processes,
)
from monitor.models import SystemSnapshot


class SystemSampler:
    def __init__(self, history_size: int = 60, alert_evaluator: AlertEvaluator | None = None) -> None:
        self.alert_evaluator = alert_evaluator or AlertEvaluator()
        self.history: deque[SystemSnapshot] = deque(maxlen=history_size)
        self._previous_snapshot_time: datetime | None = None
        self._previous_net_sent: int | None = None
        self._previous_net_recv: int | None = None

    def sample(self) -> SystemSnapshot:
        timestamp = datetime.now()
        sent, recv = collect_network_counters()
        gpu_info = collect_gpu_info()
        sent_rate, recv_rate = self._compute_network_rates(timestamp, sent, recv)
        snapshot = SystemSnapshot(
            timestamp=timestamp,
            cpu_percent=collect_cpu_percent(),
            per_cpu_percent=collect_per_cpu_percent(),
            memory_percent=collect_memory_percent(),
            disk_percent=collect_disk_percent(),
            net_bytes_sent=sent,
            net_bytes_recv=recv,
            net_sent_rate=sent_rate,
            net_recv_rate=recv_rate,
            alerts=[],
            gpu_info=gpu_info,
            top_processes=collect_top_processes(),
        )
        snapshot.alerts = self.alert_evaluator.evaluate(snapshot)
        self.history.append(snapshot)
        return snapshot

    def _compute_network_rates(
        self,
        timestamp: datetime,
        sent: int,
        recv: int,
    ) -> tuple[float, float]:
        if self._previous_snapshot_time is None:
            self._previous_snapshot_time = timestamp
            self._previous_net_sent = sent
            self._previous_net_recv = recv
            return 0.0, 0.0

        elapsed_seconds = max(
            (timestamp - self._previous_snapshot_time).total_seconds(),
            1e-6,
        )
        sent_rate = max(sent - (self._previous_net_sent or 0), 0) / elapsed_seconds
        recv_rate = max(recv - (self._previous_net_recv or 0), 0) / elapsed_seconds

        self._previous_snapshot_time = timestamp
        self._previous_net_sent = sent
        self._previous_net_recv = recv
        return sent_rate, recv_rate

    def summarize_recent_trends(self, points: int = 5) -> dict[str, str]:
        recent = list(self.history)[-points:]
        return {
            "cpu": self._trend_string([snapshot.cpu_percent for snapshot in recent]),
            "memory": self._trend_string([snapshot.memory_percent for snapshot in recent]),
            "network_up": self._trend_string([snapshot.net_sent_rate for snapshot in recent]),
            "network_down": self._trend_string([snapshot.net_recv_rate for snapshot in recent]),
        }

    @staticmethod
    def _trend_string(values: list[float]) -> str:
        if not values:
            return "n/a"

        minimum = min(values)
        maximum = max(values)
        if maximum - minimum < 1e-9:
            return "▁" * len(values)

        blocks = "▁▂▃▄▅▆▇█"
        trend_chars: list[str] = []
        for value in values:
            normalized = (value - minimum) / (maximum - minimum)
            index = min(int(normalized * (len(blocks) - 1)), len(blocks) - 1)
            trend_chars.append(blocks[index])

        return "".join(trend_chars)
