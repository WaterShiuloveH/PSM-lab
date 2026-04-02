from __future__ import annotations

from monitor.models import SystemSnapshot


def _format_rate(num_bytes_per_second: float) -> str:
    units = ["B/s", "KB/s", "MB/s", "GB/s"]
    value = num_bytes_per_second

    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:0.2f} {unit}"
        value /= 1024

    return f"{value:0.2f} GB/s"


def render_snapshot(snapshot: SystemSnapshot, trends: dict[str, str] | None = None) -> str:
    max_cores_to_show = 8
    shown_cores = snapshot.per_cpu_percent[:max_cores_to_show]
    remaining_cores = len(snapshot.per_cpu_percent) - len(shown_cores)
    per_core_summary = ", ".join(
        f"c{index}:{usage:>5.1f}%"
        for index, usage in enumerate(shown_cores)
    )
    if remaining_cores > 0:
        per_core_summary = f"{per_core_summary}, +{remaining_cores} more"

    trends = trends or {}

    lines = [
        f"Time: {snapshot.timestamp:%Y-%m-%d %H:%M:%S}",
        "=" * 48,
        f"CPU:    {snapshot.cpu_percent:>6.2f}%",
        f"Memory: {snapshot.memory_percent:>6.2f}%",
        f"Disk:   {snapshot.disk_percent:>6.2f}%",
        f"Net Up:   {_format_rate(snapshot.net_sent_rate)}",
        f"Net Down: {_format_rate(snapshot.net_recv_rate)}",
        f"Net Sent Total: {snapshot.net_bytes_sent} bytes",
        f"Net Recv Total: {snapshot.net_bytes_recv} bytes",
        "",
        "Recent Trends:",
        "  Legend: low -> high | ▁▂▃▄▅▆▇█",
        f"  CPU:      {trends.get('cpu', 'n/a')}",
        f"  Memory:   {trends.get('memory', 'n/a')}",
        f"  Net Up:   {trends.get('network_up', 'n/a')}",
        f"  Net Down: {trends.get('network_down', 'n/a')}",
        "",
        f"Per-Core: {per_core_summary or 'unavailable'}",
        "",
        "Alerts:",
    ]

    if snapshot.alerts:
        lines.extend(f"  - {alert}" for alert in snapshot.alerts)
    else:
        lines.append("  - none")

    lines.extend(["", "GPUs:"])
    if snapshot.gpu_info:
        for gpu in snapshot.gpu_info:
            lines.append(
                f"  {gpu.name}: util={gpu.utilization_percent:>5.1f}% "
                f"mem={gpu.memory_used_mb}/{gpu.memory_total_mb} MB"
            )
    else:
        lines.append("  none detected")

    lines.extend(["", "Top Processes:"])
    for process in snapshot.top_processes:
        lines.append(
            f"  PID={process.pid:<6} "
            f"CPU={process.cpu_percent:>6.2f}% "
            f"MEM={process.memory_percent:>6.2f}% "
            f"{process.name}"
        )

    return "\n".join(lines)
