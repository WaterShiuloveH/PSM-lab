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
            ]
        )

        self.assertEqual(args.interval, 2.5)
        self.assertEqual(args.history_size, 120)
        self.assertEqual(args.process_refresh_interval, 4.0)
        self.assertEqual(args.gpu_refresh_interval, 6.0)
        self.assertEqual(args.cpu_threshold, 75.0)
        self.assertEqual(args.memory_threshold, 70.0)
        self.assertEqual(args.disk_threshold, 80.0)


class MainRuntimeTest(TestCase):
    @patch("main.time.sleep", side_effect=[None, KeyboardInterrupt])
    @patch("main.render_snapshot", return_value="snapshot")
    @patch("main.clear_screen")
    @patch("main.SystemSampler")
    @patch("main.parse_args")
    def test_main_uses_sampler_trends_when_rendering(
        self,
        mock_parse_args,
        mock_system_sampler,
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
        )
        sampler = Mock()
        sampler.sample.return_value = Mock()
        sampler.summarize_recent_trends.return_value = {"cpu": ".-#"}
        mock_system_sampler.return_value = sampler

        with self.assertRaises(KeyboardInterrupt):
            main([])

        mock_render_snapshot.assert_called_once_with(
            sampler.sample.return_value,
            trends={"cpu": ".-#"},
        )
        mock_system_sampler.assert_called_once()
