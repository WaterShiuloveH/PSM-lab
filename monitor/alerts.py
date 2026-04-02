from __future__ import annotations

from monitor.models import SystemSnapshot


class AlertEvaluator:
    def __init__(
        self,
        cpu_threshold: float = 90.0,
        memory_threshold: float = 85.0,
        disk_threshold: float = 90.0,
    ) -> None:
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold

    def evaluate(self, snapshot: SystemSnapshot) -> list[str]:
        alerts: list[str] = []

        if snapshot.cpu_percent >= self.cpu_threshold:
            alerts.append(f"High CPU usage: {snapshot.cpu_percent:.1f}%")
        if snapshot.memory_percent >= self.memory_threshold:
            alerts.append(f"High memory usage: {snapshot.memory_percent:.1f}%")
        if snapshot.disk_percent >= self.disk_threshold:
            alerts.append(f"High disk usage: {snapshot.disk_percent:.1f}%")

        for gpu in snapshot.gpu_info:
            if gpu.utilization_percent >= self.cpu_threshold:
                alerts.append(f"High GPU usage on {gpu.name}: {gpu.utilization_percent:.1f}%")

        return alerts
