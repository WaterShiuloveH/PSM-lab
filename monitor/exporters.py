from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from monitor.models import GpuInfo, ProcessInfo, SystemSnapshot


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


class SqliteSnapshotExporter(SnapshotExporter):
    def __init__(self, path: str, retention_max_rows: int | None = None) -> None:
        self.path = path
        self.retention_max_rows = retention_max_rows
        self._connection = sqlite3.connect(path)
        initialize_sqlite_schema(self._connection)

    def write(self, snapshot: SystemSnapshot) -> None:
        record = snapshot_to_record(snapshot)
        self._connection.execute(
            """
            INSERT INTO snapshots (
                timestamp,
                cpu_percent,
                per_cpu_percent,
                memory_percent,
                disk_percent,
                net_bytes_sent,
                net_bytes_recv,
                net_sent_rate,
                net_recv_rate,
                net_sent_rate_smoothed,
                net_recv_rate_smoothed,
                alerts,
                gpu_info,
                top_processes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["timestamp"],
                record["cpu_percent"],
                json.dumps(record["per_cpu_percent"]),
                record["memory_percent"],
                record["disk_percent"],
                record["net_bytes_sent"],
                record["net_bytes_recv"],
                record["net_sent_rate"],
                record["net_recv_rate"],
                record["net_sent_rate_smoothed"],
                record["net_recv_rate_smoothed"],
                json.dumps(record["alerts"]),
                json.dumps(record["gpu_info"]),
                json.dumps(record["top_processes"]),
            ),
        )
        if self.retention_max_rows is not None:
            prune_sqlite_rows(self._connection, self.retention_max_rows)
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()


def create_exporter(
    path: str | None,
    export_format: str,
    retention_max_rows: int | None = None,
) -> SnapshotExporter | None:
    if not path:
        return None
    if export_format == "json":
        return JsonSnapshotExporter(path)
    if export_format == "csv":
        return CsvSnapshotExporter(path)
    if export_format == "sqlite":
        return SqliteSnapshotExporter(path, retention_max_rows=retention_max_rows)
    raise ValueError(f"Unsupported export format: {export_format}")


def snapshot_to_record(snapshot: SystemSnapshot) -> dict[str, object]:
    record = asdict(snapshot)
    record["timestamp"] = snapshot.timestamp.isoformat()
    return record


def initialize_sqlite_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            cpu_percent REAL NOT NULL,
            per_cpu_percent TEXT NOT NULL,
            memory_percent REAL NOT NULL,
            disk_percent REAL NOT NULL,
            net_bytes_sent INTEGER NOT NULL,
            net_bytes_recv INTEGER NOT NULL,
            net_sent_rate REAL NOT NULL,
            net_recv_rate REAL NOT NULL,
            net_sent_rate_smoothed REAL NOT NULL,
            net_recv_rate_smoothed REAL NOT NULL,
            alerts TEXT NOT NULL,
            gpu_info TEXT NOT NULL,
            top_processes TEXT NOT NULL
        )
        """
    )
    connection.commit()


def prune_sqlite_rows(connection: sqlite3.Connection, max_rows: int) -> None:
    if max_rows <= 0:
        return
    connection.execute(
        """
        DELETE FROM snapshots
        WHERE id NOT IN (
            SELECT id FROM snapshots
            ORDER BY id DESC
            LIMIT ?
        )
        """,
        (max_rows,),
    )


def load_sqlite_history(
    path: str,
    limit: int,
    since: str | None = None,
    before: str | None = None,
) -> list[SystemSnapshot]:
    connection = sqlite3.connect(path)
    try:
        query = """
            SELECT
                timestamp,
                cpu_percent,
                per_cpu_percent,
                memory_percent,
                disk_percent,
                net_bytes_sent,
                net_bytes_recv,
                net_sent_rate,
                net_recv_rate,
                net_sent_rate_smoothed,
                net_recv_rate_smoothed,
                alerts,
                gpu_info,
                top_processes
            FROM snapshots
        """
        conditions: list[str] = []
        params: list[object] = []
        if since is not None:
            conditions.append("timestamp >= ?")
            params.append(since)
        if before is not None:
            conditions.append("timestamp <= ?")
            params.append(before)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = connection.execute(query, tuple(params)).fetchall()
    finally:
        connection.close()

    snapshots = [_snapshot_from_sqlite_row(row) for row in reversed(rows)]
    return snapshots


def load_sqlite_latest(
    path: str,
    since: str | None = None,
    before: str | None = None,
) -> SystemSnapshot | None:
    connection = sqlite3.connect(path)
    try:
        query = """
            SELECT
                timestamp,
                cpu_percent,
                per_cpu_percent,
                memory_percent,
                disk_percent,
                net_bytes_sent,
                net_bytes_recv,
                net_sent_rate,
                net_recv_rate,
                net_sent_rate_smoothed,
                net_recv_rate_smoothed,
                alerts,
                gpu_info,
                top_processes
            FROM snapshots
        """
        conditions: list[str] = []
        params: list[object] = []
        if since is not None:
            conditions.append("timestamp >= ?")
            params.append(since)
        if before is not None:
            conditions.append("timestamp <= ?")
            params.append(before)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY id DESC LIMIT 1"
        row = connection.execute(query, tuple(params)).fetchone()
    finally:
        connection.close()

    if row is None:
        return None
    return _snapshot_from_sqlite_row(row)


def _snapshot_from_sqlite_row(row: tuple[object, ...]) -> SystemSnapshot:
    timestamp = datetime.fromisoformat(str(row[0]))
    per_cpu_percent = [float(value) for value in json.loads(str(row[2]))]
    alerts = [str(value) for value in json.loads(str(row[11]))]
    gpu_info = [
        GpuInfo(
            name=str(item["name"]),
            utilization_percent=float(item["utilization_percent"]),
            memory_used_mb=int(item["memory_used_mb"]),
            memory_total_mb=int(item["memory_total_mb"]),
        )
        for item in json.loads(str(row[12]))
    ]
    top_processes = [
        ProcessInfo(
            pid=int(item["pid"]),
            name=str(item["name"]),
            cpu_percent=float(item["cpu_percent"]),
            memory_percent=float(item["memory_percent"]),
        )
        for item in json.loads(str(row[13]))
    ]
    return SystemSnapshot(
        timestamp=timestamp,
        cpu_percent=float(row[1]),
        per_cpu_percent=per_cpu_percent,
        memory_percent=float(row[3]),
        disk_percent=float(row[4]),
        net_bytes_sent=int(row[5]),
        net_bytes_recv=int(row[6]),
        net_sent_rate=float(row[7]),
        net_recv_rate=float(row[8]),
        net_sent_rate_smoothed=float(row[9]),
        net_recv_rate_smoothed=float(row[10]),
        alerts=alerts,
        gpu_info=gpu_info,
        top_processes=top_processes,
    )
