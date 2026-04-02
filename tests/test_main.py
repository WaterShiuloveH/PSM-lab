from __future__ import annotations

from unittest import TestCase

from main import parse_args


class MainArgsTest(TestCase):
    def test_parse_args_uses_defaults(self) -> None:
        args = parse_args([])

        self.assertEqual(args.interval, 1.0)
        self.assertEqual(args.history_size, 60)
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
        self.assertEqual(args.cpu_threshold, 75.0)
        self.assertEqual(args.memory_threshold, 70.0)
        self.assertEqual(args.disk_threshold, 80.0)
