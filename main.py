from __future__ import annotations

import argparse
import os
import sys
import time

from monitor.api import ApiServerHandle, create_api_server
from monitor.alerts import AlertEvaluator
from monitor.exporters import create_exporter, load_sqlite_history, load_sqlite_latest
from monitor.sampler import SystemSampler
from monitor.ui import render_snapshot


def clear_screen() -> None:
    os.system("clear")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Linux system monitor in Python")
    parser.add_argument("--interval", type=float, default=1.0, help="Refresh interval in seconds")
    parser.add_argument("--history-size", type=int, default=60, help="Number of snapshots to keep")
    parser.add_argument(
        "--process-refresh-interval",
        type=float,
        default=3.0,
        help="Refresh interval for top-process collection in seconds",
    )
    parser.add_argument(
        "--gpu-refresh-interval",
        type=float,
        default=5.0,
        help="Refresh interval for GPU collection in seconds",
    )
    parser.add_argument("--cpu-threshold", type=float, default=90.0, help="CPU alert threshold")
    parser.add_argument("--memory-threshold", type=float, default=85.0, help="Memory alert threshold")
    parser.add_argument("--disk-threshold", type=float, default=90.0, help="Disk alert threshold")
    parser.add_argument(
        "--alert-sustain-samples",
        type=int,
        default=3,
        help="Number of consecutive samples required before firing an alert",
    )
    parser.add_argument(
        "--alert-cooldown-seconds",
        type=float,
        default=30.0,
        help="Cooldown window before repeating the same alert",
    )
    parser.add_argument("--http-host", type=str, default="127.0.0.1", help="HTTP API bind host")
    parser.add_argument("--http-port", type=int, default=0, help="Optional HTTP API port")
    parser.add_argument("--export-file", type=str, default=None, help="Optional export file path")
    parser.add_argument(
        "--export-format",
        choices=("json", "csv", "sqlite"),
        default="json",
        help="Export format when --export-file is set",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    sampler = SystemSampler(
        history_size=args.history_size,
        alert_evaluator=AlertEvaluator(
            cpu_threshold=args.cpu_threshold,
            memory_threshold=args.memory_threshold,
            disk_threshold=args.disk_threshold,
            sustain_samples=args.alert_sustain_samples,
            cooldown_seconds=args.alert_cooldown_seconds,
        ),
        process_refresh_interval=args.process_refresh_interval,
        gpu_refresh_interval=args.gpu_refresh_interval,
    )
    exporter = create_exporter(args.export_file, args.export_format)
    api_handle = None

    def memory_latest_snapshot_provider(*, since=None, before=None):
        history = memory_history_provider(limit=len(sampler.history), since=since, before=before)
        return history[-1] if history else None

    def memory_history_provider(*, limit: int, since=None, before=None):
        history = list(sampler.history)
        if since is not None:
            history = [snapshot for snapshot in history if snapshot.timestamp.isoformat() >= since]
        if before is not None:
            history = [snapshot for snapshot in history if snapshot.timestamp.isoformat() <= before]
        return history[-limit:]

    if args.http_port:
        if args.export_format == "sqlite" and args.export_file:
            latest_snapshot_provider = lambda *, since=None, before=None: load_sqlite_latest(
                args.export_file,
                since=since,
                before=before,
            )
            history_provider = lambda *, limit, since=None, before=None: load_sqlite_history(
                args.export_file,
                limit,
                since=since,
                before=before,
            )
        else:
            latest_snapshot_provider = memory_latest_snapshot_provider
            history_provider = memory_history_provider
        api_server = create_api_server(
            args.http_host,
            args.http_port,
            latest_snapshot_provider=latest_snapshot_provider,
            history_provider=history_provider,
        )
        api_handle = ApiServerHandle(api_server)
        api_handle.start()

    try:
        # Prime process CPU percentages so later samples become meaningful.
        sampler.sample()
        time.sleep(args.interval)

        while True:
            snapshot = sampler.sample()
            if exporter is not None:
                exporter.write(snapshot)
            clear_screen()
            print(render_snapshot(snapshot, trends=sampler.summarize_recent_trends()))
            time.sleep(args.interval)
    finally:
        if api_handle is not None:
            api_handle.close()
        if exporter is not None:
            exporter.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMonitor stopped.", file=sys.stderr)
