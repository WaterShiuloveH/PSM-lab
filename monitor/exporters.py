from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from monitor.models import SystemSnapshot


class SnapshotExporter:
    def write(self, snapshot: SystemSnapshot) -> None:
        raise NotImplementedError

    def close(self) -> None:
        return None


class JsonSnapshotExporter(SnapshotExporter):
    def __init__(self, path: str) -> None:
        self._file = Path(path).open("a", encoding="utf-8")

    def write(self, snapshot: SystemSnapshot) -> None:
        self._file.write(json.dumps(snapshot_to_record(snapshot)) + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()


class CsvSnapshotExporter(SnapshotExporter):
    FIELDNAMES = [
        "timestamp",
        "cpu_percent",
        "per_cpu_percent",
        "memory_percent",
        "disk_percent",
        "net_bytes_sent",
        "net_bytes_recv",
        "net_sent_rate",
        "net_recv_rate",
        "net_sent_rate_smoothed",
        "net_recv_rate_smoothed",
        "alerts",
        "gpu_info",
        "top_processes",
    ]

    def __init__(self, path: str) -> None:
        file_path = Path(path)
        has_content = file_path.exists() and file_path.stat().st_size > 0
        self._file = file_path.open("a", encoding="utf-8", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=self.FIELDNAMES)
        if not has_content:
            self._writer.writeheader()
            self._file.flush()

    def write(self, snapshot: SystemSnapshot) -> None:
        record = snapshot_to_record(snapshot)
        row = {
            "timestamp": record["timestamp"],
            "cpu_percent": record["cpu_percent"],
            "per_cpu_percent": json.dumps(record["per_cpu_percent"]),
            "memory_percent": record["memory_percent"],
            "disk_percent": record["disk_percent"],
            "net_bytes_sent": record["net_bytes_sent"],
            "net_bytes_recv": record["net_bytes_recv"],
            "net_sent_rate": record["net_sent_rate"],
            "net_recv_rate": record["net_recv_rate"],
            "net_sent_rate_smoothed": record["net_sent_rate_smoothed"],
            "net_recv_rate_smoothed": record["net_recv_rate_smoothed"],
            "alerts": json.dumps(record["alerts"]),
            "gpu_info": json.dumps(record["gpu_info"]),
            "top_processes": json.dumps(record["top_processes"]),
        }
        self._writer.writerow(row)
        self._file.flush()

    def close(self) -> None:
        self._file.close()


def create_exporter(path: str | None, export_format: str) -> SnapshotExporter | None:
    if not path:
        return None
    if export_format == "json":
        return JsonSnapshotExporter(path)
    if export_format == "csv":
        return CsvSnapshotExporter(path)
    raise ValueError(f"Unsupported export format: {export_format}")


def snapshot_to_record(snapshot: SystemSnapshot) -> dict[str, object]:
    record = asdict(snapshot)
    record["timestamp"] = snapshot.timestamp.isoformat()
    return record
