from __future__ import annotations

import shutil
import subprocess
from typing import Iterable

import psutil

from monitor.models import GpuInfo, ProcessInfo


def collect_cpu_percent() -> float:
    return psutil.cpu_percent(interval=None)


def collect_per_cpu_percent() -> list[float]:
    return list(psutil.cpu_percent(interval=None, percpu=True))


def collect_memory_percent() -> float:
    return psutil.virtual_memory().percent


def collect_disk_percent(path: str = "/") -> float:
    return psutil.disk_usage(path).percent


def collect_network_counters() -> tuple[int, int]:
    counters = psutil.net_io_counters()
    return counters.bytes_sent, counters.bytes_recv


def collect_top_processes(limit: int = 5) -> list[ProcessInfo]:
    processes: list[ProcessInfo] = []

    try:
        for proc in _iter_processes():
            try:
                info = proc.info
                processes.append(
                    ProcessInfo(
                        pid=info["pid"],
                        name=info["name"] or "unknown",
                        cpu_percent=float(info["cpu_percent"] or 0.0),
                        memory_percent=float(info["memory_percent"] or 0.0),
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except PermissionError:
        # Some environments restrict process enumeration; degrade gracefully.
        return []

    processes.sort(key=lambda proc: (proc.cpu_percent, proc.memory_percent), reverse=True)
    return processes[:limit]


def collect_gpu_info() -> list[GpuInfo]:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return []

    try:
        completed = subprocess.run(
            [
                nvidia_smi,
                "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    gpu_info: list[GpuInfo] = []
    for line in completed.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 4:
            continue

        name, utilization, memory_used, memory_total = parts
        try:
            gpu_info.append(
                GpuInfo(
                    name=name,
                    utilization_percent=float(utilization),
                    memory_used_mb=int(memory_used),
                    memory_total_mb=int(memory_total),
                )
            )
        except ValueError:
            continue

    return gpu_info


def _iter_processes() -> Iterable[psutil.Process]:
    return psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"])
