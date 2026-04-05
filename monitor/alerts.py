from __future__ import annotations

from datetime import datetime

from monitor.models import SystemSnapshot


class AlertEvaluator:
    def __init__(
        self,
        cpu_threshold: float = 90.0,
        memory_threshold: float = 85.0,
        disk_threshold: float = 90.0,
        sustain_samples: int = 3,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
        self.sustain_samples = sustain_samples
        self.cooldown_seconds = cooldown_seconds
        self._consecutive_hits: dict[str, int] = {}
        self._last_alert_times: dict[str, datetime] = {}

    def evaluate(self, snapshot: SystemSnapshot) -> list[str]:
        alerts: list[str] = []

        self._evaluate_metric(
            alerts,
            key="cpu",
            current_value=snapshot.cpu_percent,
            threshold=self.cpu_threshold,
            message=f"High CPU usage: {snapshot.cpu_percent:.1f}%",
            timestamp=snapshot.timestamp,
        )
        self._evaluate_metric(
            alerts,
            key="memory",
            current_value=snapshot.memory_percent,
            threshold=self.memory_threshold,
            message=f"High memory usage: {snapshot.memory_percent:.1f}%",
            timestamp=snapshot.timestamp,
        )
        self._evaluate_metric(
            alerts,
            key="disk",
            current_value=snapshot.disk_percent,
            threshold=self.disk_threshold,
            message=f"High disk usage: {snapshot.disk_percent:.1f}%",
            timestamp=snapshot.timestamp,
        )

        for gpu in snapshot.gpu_info:
            self._evaluate_metric(
                alerts,
                key=f"gpu:{gpu.name}",
                current_value=gpu.utilization_percent,
                threshold=self.cpu_threshold,
                message=f"High GPU usage on {gpu.name}: {gpu.utilization_percent:.1f}%",
                timestamp=snapshot.timestamp,
            )

        return alerts

    def _evaluate_metric(
        self,
        alerts: list[str],
        key: str,
        current_value: float,
        threshold: float,
        message: str,
        timestamp: datetime,
    ) -> None:
        if current_value >= threshold:
            hits = self._consecutive_hits.get(key, 0) + 1
            self._consecutive_hits[key] = hits
            if hits >= self.sustain_samples and self._cooldown_elapsed(key, timestamp):
                alerts.append(message)
                self._last_alert_times[key] = timestamp
        else:
            self._consecutive_hits[key] = 0

    def _cooldown_elapsed(self, key: str, timestamp: datetime) -> bool:
        last_alert_time = self._last_alert_times.get(key)
        if last_alert_time is None:
            return True
        return (timestamp - last_alert_time).total_seconds() >= self.cooldown_seconds
