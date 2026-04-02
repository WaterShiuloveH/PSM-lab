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

    def sample(self) -> SystemSnapshot:
        sent, recv = collect_network_counters()
        gpu_info = collect_gpu_info()
        snapshot = SystemSnapshot(
            timestamp=datetime.now(),
            cpu_percent=collect_cpu_percent(),
            per_cpu_percent=collect_per_cpu_percent(),
            memory_percent=collect_memory_percent(),
            disk_percent=collect_disk_percent(),
            net_bytes_sent=sent,
            net_bytes_recv=recv,
            alerts=[],
            gpu_info=gpu_info,
            top_processes=collect_top_processes(),
        )
        snapshot.alerts = self.alert_evaluator.evaluate(snapshot)
        self.history.append(snapshot)
        return snapshot
