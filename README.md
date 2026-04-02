# Linux System Monitor in Python

This folder is now a small crash course plus starter project for learning system design through a practical example:

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
