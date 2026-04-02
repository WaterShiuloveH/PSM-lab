from __future__ import annotations

import os
import time

from monitor.sampler import SystemSampler
from monitor.ui import render_snapshot


def clear_screen() -> None:
    os.system("clear")


def main() -> None:
    sampler = SystemSampler(history_size=60)

    # Prime process CPU percentages so later samples become meaningful.
    sampler.sample()
    time.sleep(1)

    while True:
        snapshot = sampler.sample()
        clear_screen()
        print(render_snapshot(snapshot))
        time.sleep(1)


if __name__ == "__main__":
    main()
