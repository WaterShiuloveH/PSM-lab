from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import psutil

from monitor.collectors import (
    collect_cpu_percent,
    collect_disk_percent,
    collect_gpu_info,
    collect_memory_percent,
    collect_network_counters,
    collect_top_processes,
)


class CollectorsTest(TestCase):
    @patch("monitor.collectors.psutil.cpu_percent", return_value=27.5)
    def test_collect_cpu_percent(self, mock_cpu_percent) -> None:
        result = collect_cpu_percent()

        self.assertEqual(result, 27.5)
        mock_cpu_percent.assert_called_once_with(interval=None)

    @patch("monitor.collectors.psutil.virtual_memory")
    def test_collect_memory_percent(self, mock_virtual_memory) -> None:
        mock_virtual_memory.return_value = SimpleNamespace(percent=71.2)

        result = collect_memory_percent()

        self.assertEqual(result, 71.2)

    @patch("monitor.collectors.psutil.disk_usage")
    def test_collect_disk_percent(self, mock_disk_usage) -> None:
        mock_disk_usage.return_value = SimpleNamespace(percent=62.4)

        result = collect_disk_percent("/data")

        self.assertEqual(result, 62.4)
        mock_disk_usage.assert_called_once_with("/data")

    @patch("monitor.collectors.psutil.net_io_counters")
    def test_collect_network_counters(self, mock_net_io_counters) -> None:
        mock_net_io_counters.return_value = SimpleNamespace(bytes_sent=111, bytes_recv=222)

        result = collect_network_counters()

        self.assertEqual(result, (111, 222))

    @patch("monitor.collectors._iter_processes")
    def test_collect_top_processes_sorts_and_limits(self, mock_iter_processes) -> None:
        mock_iter_processes.return_value = [
            SimpleNamespace(
                info={"pid": 10, "name": "slow", "cpu_percent": 5.0, "memory_percent": 10.0}
            ),
            SimpleNamespace(
                info={"pid": 20, "name": "fast", "cpu_percent": 80.0, "memory_percent": 2.0}
            ),
            SimpleNamespace(
                info={"pid": 30, "name": None, "cpu_percent": 40.0, "memory_percent": 5.0}
            ),
        ]

        result = collect_top_processes(limit=2)

        self.assertEqual([proc.pid for proc in result], [20, 30])
        self.assertEqual(result[1].name, "unknown")

    @patch("monitor.collectors._iter_processes", side_effect=PermissionError)
    def test_collect_top_processes_returns_empty_when_process_access_is_blocked(
        self, mock_iter_processes
    ) -> None:
        result = collect_top_processes()

        self.assertEqual(result, [])
        mock_iter_processes.assert_called_once_with()

    @patch("monitor.collectors._iter_processes")
    def test_collect_top_processes_skips_access_denied_processes(self, mock_iter_processes) -> None:
        class DeniedProcess:
            @property
            def info(self) -> dict[str, object]:
                raise psutil.AccessDenied(pid=99)

        denied_process = DeniedProcess()
        allowed_process = SimpleNamespace(
            info={"pid": 7, "name": "python", "cpu_percent": 10.0, "memory_percent": 1.5}
        )
        mock_iter_processes.return_value = [denied_process, allowed_process]

        result = collect_top_processes()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].pid, 7)

    @patch("monitor.collectors.shutil.which", return_value=None)
    def test_collect_gpu_info_returns_empty_without_nvidia_smi(self, mock_which) -> None:
        result = collect_gpu_info()

        self.assertEqual(result, [])
        mock_which.assert_called_once_with("nvidia-smi")

    @patch("monitor.collectors.subprocess.run")
    @patch("monitor.collectors.shutil.which", return_value="/usr/bin/nvidia-smi")
    def test_collect_gpu_info_parses_nvidia_smi_output(self, mock_which, mock_run) -> None:
        mock_run.return_value = SimpleNamespace(
            stdout="GPU 0, 72, 1024, 24564\n"
        )

        result = collect_gpu_info()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "GPU 0")
        self.assertEqual(result[0].utilization_percent, 72.0)
        self.assertEqual(result[0].memory_used_mb, 1024)
        self.assertEqual(result[0].memory_total_mb, 24564)
