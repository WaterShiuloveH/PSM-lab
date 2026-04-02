from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float


@dataclass(slots=True)
class GpuInfo:
    name: str
    utilization_percent: float
    memory_used_mb: int
    memory_total_mb: int


@dataclass(slots=True)
class SystemSnapshot:
    timestamp: datetime
    cpu_percent: float
    per_cpu_percent: list[float]
    memory_percent: float
    disk_percent: float
    net_bytes_sent: int
    net_bytes_recv: int
    net_sent_rate: float
    net_recv_rate: float
    alerts: list[str]
    gpu_info: list[GpuInfo]
    top_processes: list[ProcessInfo]
