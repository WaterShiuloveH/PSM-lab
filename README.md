# Linux System Monitor in Python

This project is a Python-based terminal system monitor built to study practical system design through a real example.

It can be used in two ways:

- as a runnable Linux-style system monitor project
- as a crash-course study project for software engineering interviews

## Features

- real-time CPU, memory, disk, and network monitoring
- per-core CPU visibility
- raw and smoothed network throughput
- top process reporting
- threshold-based alerts
- recent trend sparklines in the terminal
- optional GPU collection through `nvidia-smi`
- configurable CLI flags for refresh and alert thresholds
- lower-overhead sampling with cached slow collectors
- optional snapshot export to JSON, CSV, or SQLite

## Run

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run the monitor:

```bash
python3 main.py
```

Run with custom settings:

```bash
python3 main.py \
  --interval 1 \
  --history-size 120 \
  --cpu-threshold 80 \
  --memory-threshold 80 \
  --disk-threshold 85 \
  --process-refresh-interval 3 \
  --gpu-refresh-interval 5
```

Run with export enabled:

```bash
python3 main.py --export-file snapshots.jsonl --export-format json
python3 main.py --export-file snapshots.csv --export-format csv
python3 main.py --export-file snapshots.db --export-format sqlite
```

## Test

Using the `Makefile`:

```bash
make test
make smoke
make run
make compile
make export-json
make export-csv
make export-sqlite
```

Direct commands:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall .
```

## Design Summary

The monitor is structured in layers:

- collectors gather machine data
- sampler builds time-based snapshots and rate calculations
- exporters persist snapshots to JSON, CSV, or SQLite
- alerts evaluate thresholds
- UI renders a terminal dashboard
- `main.py` wires configuration and runtime behavior together

The sampler treats collectors by cost:

- fast collectors refresh every sample
- slow collectors such as process and GPU queries are cached and refreshed less often

For network throughput, the monitor keeps both:

- raw per-sample rates for fidelity
- smoothed rates for a steadier terminal display

Generated snapshot export files are ignored by git by default:

- `snapshots.jsonl`
- `snapshots.csv`
- `snapshots.db`

This folder also includes a small crash course for learning system design through the same example:

- Build a Linux system monitor
- Explain the design clearly in an interview
- Practice common system design tradeoffs for software engineering interviews

## 1. Interview framing

If an interviewer asks you to design a Linux system monitor, do not jump straight into code.

Use this order:

1. Clarify scope
2. Define functional requirements
3. Define non-functional requirements
4. Draw the high-level architecture
5. Explain components and tradeoffs
6. Talk about scaling, failure handling, and extensions

### Functional requirements

- Show CPU usage
- Show memory usage
- Show disk usage
- Show network throughput
- Show top processes by CPU or memory
- Refresh every N seconds
- Optionally store historical metrics
- Optionally expose alerts
- Optionally configure thresholds and refresh intervals from the command line

### Non-functional requirements

- Low overhead on the monitored machine
- High refresh accuracy
- Easy to extend with new collectors
- Safe access to Linux system information
- Works on most Linux distributions

## 2. High-level design

Think in layers:

- Collector layer
  - Reads metrics from `/proc`, `/sys`, or `psutil`
- Aggregation layer
  - Normalizes raw samples into a common model
- Storage layer
  - Keeps rolling in-memory history or persists to SQLite
- Presentation layer
  - CLI, terminal dashboard, web API, or GUI
- Alerting layer
  - Triggers warnings when thresholds are exceeded

For a junior-to-mid interview, this is already a strong structure.

## 3. What to say in the interview

### Scope clarification

Ask:

- Is this for one machine or many machines?
- Real-time only, or do we need historical trends too?
- Terminal UI, GUI, or HTTP API?
- Do we need alerts?
- What refresh interval is acceptable?

### Good default assumption

"I’ll design a single-node Linux monitor in Python with a terminal UI, 1-second refresh, top processes, and optional short-term history."

That answer sounds practical and focused.

## 4. Core tradeoffs

### `/proc` vs `psutil`

- `/proc`
  - Faster, more Linux-native, better for deep OS understanding
  - More manual parsing work
- `psutil`
  - Faster to build, portable, interview-friendly
  - Slight abstraction overhead

Strong interview answer:

"I would start with `psutil` for productivity, then replace hot paths with direct `/proc` parsing if profiling shows overhead."

### Pull model vs push model

- Pull
  - A scheduler samples the machine every second
  - Best for a local monitor
- Push
  - Agents send metrics elsewhere
  - Better for fleet monitoring

### In-memory history vs database

- In-memory ring buffer
  - Very fast
  - Good for recent charts
- SQLite / time-series storage
  - Useful for historical analysis
  - More complexity

## 5. Step-by-step build plan

### Step 1. Build the data model

Define a snapshot object containing:

- timestamp
- cpu_percent
- memory_percent
- disk_percent
- network bytes sent/received
- top processes

### Step 2. Implement collectors

Create separate collectors for:

- CPU
- Memory
- Disk
- Network
- Processes

Why this matters:

- Easier testing
- Easier extension
- Cleaner interview explanation

### Step 3. Add a sampler loop

Use a fixed interval such as 1 second:

- read all collectors
- build one snapshot
- append to history
- render output

### Step 4. Add a rolling history buffer

Keep the latest 60 or 300 snapshots.

This supports:

- trend charts
- alert calculations
- future export features

### Step 5. Render the UI

Start simple:

- clear terminal
- print summary metrics
- print top processes

Later options:

- `rich`
- `textual`
- Flask/FastAPI web dashboard

### Step 6. Add alerting

Examples:

- CPU > 90% for 3 samples
- Memory > 85%
- Disk > 90%

The current starter now includes a simple threshold-based alert evaluator and a GPU collector hook via `nvidia-smi`, which is a useful extension point to talk through in interviews.

### Step 7. Discuss production hardening

Mention:

- permissions
- collector timeouts
- sampling jitter
- clock consistency
- missing metrics
- logging and observability

## 6. Scaling the design

If the interviewer asks how to scale from one machine to thousands:

- Run an agent on each host
- Send metrics to Kafka or a message queue
- Store in Prometheus, ClickHouse, or a time-series DB
- Build dashboards on top
- Add alerting rules centrally

This turns the design from `top` into a distributed monitoring platform.

## 7. Interview angle

For performance-oriented systems roles, emphasize:

- performance awareness
- efficient data collection
- low system overhead
- concurrency tradeoffs
- Linux internals knowledge
- observability and reliability

Good talking points:

- avoid blocking the UI during sampling
- separate collection from rendering
- use threads or async only when they simplify bottlenecks
- profile before optimizing
- understand CPU, memory, IO, and process scheduling basics

## 8. A strong answer template

Use this structure in the interview:

"I’d design this in five parts: collectors, sampler, aggregator, storage, and presentation. For a first version, I’d target a single Linux host with 1-second refresh and terminal output. I’d use `psutil` for portability and development speed, while keeping the collector interfaces abstract so we can switch some metrics to direct `/proc` parsing later if performance matters. I’d store recent snapshots in a ring buffer, expose top processes, and add threshold-based alerts. If we needed to scale to many hosts, I’d move to an agent-based architecture with centralized ingestion and time-series storage."

Practice saying that out loud.

## 9. Coding roadmap

Start with this order:

1. `models.py`
2. `collectors.py`
3. `sampler.py`
4. `ui.py`
5. `main.py`

That structure is already created under `monitor/`.

## 10. Practice questions

Prepare answers for:

1. Why use Python for this tool?
2. When would you choose `/proc` instead of `psutil`?
3. How do you reduce monitor overhead?
4. How would you test collector accuracy?
5. How would you scale from local monitor to fleet monitoring?
6. How would you handle collector failures?
7. What if one metric is slow to fetch?

## 11. Best way to study this quickly

Today:

1. Read this README once
2. Walk through the code in `monitor/`
3. Run the program and explain each module aloud
4. Practice the strong answer template 5 times
5. Do one mock interview where you start from requirements before code

## 12. Next upgrade ideas

- sparkline charts
- per-core CPU metrics
- GPU metrics
- JSON export
- REST API
- SQLite history
- anomaly detection

GPU metrics are especially relevant if you want to position this project as a more advanced systems monitoring tool.
