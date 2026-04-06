PYTHON ?= python3

.PHONY: test smoke run compile export-json export-csv export-sqlite api api-sqlite test-alerts

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

export-sqlite:
	$(PYTHON) main.py --export-file snapshots.db --export-format sqlite

api:
	$(PYTHON) main.py --http-port 8000

api-sqlite:
	$(PYTHON) main.py --export-file snapshots.db --export-format sqlite --http-port 8000

test-alerts:
	$(PYTHON) main.py --cpu-threshold 1 --memory-threshold 1 --disk-threshold 1 --alert-sustain-samples 2 --alert-cooldown-seconds 5
