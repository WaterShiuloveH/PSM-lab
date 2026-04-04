from __future__ import annotations

import argparse
import os
import sys
import time

from monitor.alerts import AlertEvaluator
from monitor.exporters import create_exporter
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
        ),
        process_refresh_interval=args.process_refresh_interval,
        gpu_refresh_interval=args.gpu_refresh_interval,
    )
    exporter = create_exporter(args.export_file, args.export_format)

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
        if exporter is not None:
            exporter.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMonitor stopped.", file=sys.stderr)
