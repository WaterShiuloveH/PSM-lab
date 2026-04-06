from __future__ import annotations

from argparse import Namespace
from unittest import TestCase
from unittest.mock import Mock
from unittest.mock import patch

from main import main
from main import parse_args


class MainArgsTest(TestCase):
    def test_parse_args_uses_defaults(self) -> None:
        args = parse_args([])

        self.assertEqual(args.interval, 1.0)
        self.assertEqual(args.history_size, 60)
        self.assertEqual(args.process_refresh_interval, 3.0)
        self.assertEqual(args.gpu_refresh_interval, 5.0)
        self.assertEqual(args.cpu_threshold, 90.0)
        self.assertEqual(args.memory_threshold, 85.0)
        self.assertEqual(args.disk_threshold, 90.0)
        self.assertEqual(args.alert_sustain_samples, 3)
        self.assertEqual(args.alert_cooldown_seconds, 30.0)
        self.assertEqual(args.http_host, "127.0.0.1")
        self.assertEqual(args.http_port, 0)
        self.assertIsNone(args.export_file)
        self.assertEqual(args.export_format, "json")

    def test_parse_args_accepts_custom_values(self) -> None:
        args = parse_args(
            [
                "--interval",
                "2.5",
                "--history-size",
                "120",
                "--process-refresh-interval",
                "4",
                "--gpu-refresh-interval",
                "6",
                "--cpu-threshold",
                "75",
                "--memory-threshold",
                "70",
                "--disk-threshold",
                "80",
                "--alert-sustain-samples",
                "5",
                "--alert-cooldown-seconds",
                "45",
                "--http-host",
                "0.0.0.0",
                "--http-port",
                "8000",
                "--export-file",
                "snapshots.db",
                "--export-format",
                "sqlite",
            ]
        )

        self.assertEqual(args.interval, 2.5)
        self.assertEqual(args.history_size, 120)
        self.assertEqual(args.process_refresh_interval, 4.0)
        self.assertEqual(args.gpu_refresh_interval, 6.0)
        self.assertEqual(args.cpu_threshold, 75.0)
        self.assertEqual(args.memory_threshold, 70.0)
        self.assertEqual(args.disk_threshold, 80.0)
        self.assertEqual(args.alert_sustain_samples, 5)
        self.assertEqual(args.alert_cooldown_seconds, 45.0)
        self.assertEqual(args.http_host, "0.0.0.0")
        self.assertEqual(args.http_port, 8000)
        self.assertEqual(args.export_file, "snapshots.db")
        self.assertEqual(args.export_format, "sqlite")


class MainRuntimeTest(TestCase):
    @patch("main.time.sleep", side_effect=[None, KeyboardInterrupt])
    @patch("main.render_snapshot", return_value="snapshot")
    @patch("main.clear_screen")
    @patch("main.ApiServerHandle")
    @patch("main.create_api_server")
    @patch("main.create_exporter")
    @patch("main.load_sqlite_history")
    @patch("main.load_sqlite_latest")
    @patch("main.SystemSampler")
    @patch("main.parse_args")
    def test_main_uses_sampler_trends_when_rendering(
        self,
        mock_parse_args,
        mock_system_sampler,
        mock_load_sqlite_latest,
        mock_load_sqlite_history,
        mock_create_exporter,
        mock_create_api_server,
        mock_api_server_handle,
        mock_clear_screen,
        mock_render_snapshot,
        mock_sleep,
    ) -> None:
        mock_parse_args.return_value = Namespace(
            interval=1.0,
            history_size=10,
            process_refresh_interval=3.0,
            gpu_refresh_interval=5.0,
            cpu_threshold=90.0,
            memory_threshold=85.0,
            disk_threshold=90.0,
            alert_sustain_samples=3,
            alert_cooldown_seconds=30.0,
            http_host="127.0.0.1",
            http_port=8000,
            export_file="out.db",
            export_format="sqlite",
        )
        sampler = Mock()
        sampler.sample.return_value = Mock()
        sampler.summarize_recent_trends.return_value = {"cpu": ".-#"}
        mock_system_sampler.return_value = sampler
        exporter = Mock()
        mock_create_exporter.return_value = exporter
        api_handle = Mock()
        mock_api_server_handle.return_value = api_handle
        mock_load_sqlite_latest.return_value = None
        mock_load_sqlite_history.return_value = []

        with self.assertRaises(KeyboardInterrupt):
            main([])

        mock_render_snapshot.assert_called_once_with(
            sampler.sample.return_value,
            trends={"cpu": ".-#"},
        )
        mock_create_api_server.assert_called_once()
        self.assertEqual(mock_create_api_server.call_args.kwargs["latest_snapshot_provider"](), None)
        self.assertEqual(mock_create_api_server.call_args.kwargs["history_provider"](5), [])
        api_handle.start.assert_called_once()
        api_handle.close.assert_called_once()
        exporter.write.assert_called_once_with(sampler.sample.return_value)
        exporter.close.assert_called_once()
        mock_system_sampler.assert_called_once()
