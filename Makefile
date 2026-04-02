PYTHON ?= python3

.PHONY: test smoke run compile export-json export-csv

test:
	$(PYTHON) -m unittest discover -s tests -v

smoke:
	$(PYTHON) -c 'from monitor.sampler import SystemSampler; from monitor.ui import render_snapshot; import time; s=SystemSampler(); s.sample(); time.sleep(1); print(render_snapshot(s.sample()))'

run:
	$(PYTHON) main.py

compile:
	$(PYTHON) -m compileall .

export-json:
	$(PYTHON) main.py --export-file snapshots.jsonl --export-format json

export-csv:
	$(PYTHON) main.py --export-file snapshots.csv --export-format csv
