# Cloud Infrastructure Anomaly Detection

A synthetic, self-generated dataset and anomaly detection pipeline modelling behavioural baselines across a simplified multi-tier cloud deployment — framed as a lightweight AIOps / infrastructure health monitoring system.

## Why synthetic data

Rather than downloading a pre-labelled dataset, this project generates its own data from scratch using a Python simulator. This forces an explicit understanding of what "normal" and "abnormal" infrastructure behaviour actually look like — the values below aren't arbitrary, each one is tied to a reason grounded in what that server type's job actually is

## Architecture

The dataset models a small, realistic slice of a cloud-hosted application:

```
user traffic → load balancer → web servers → cache (fast path) → database (persistent storage)
                                                                              ↑
                                                        batch/worker (offline, scheduled processing)
```

Five server types, three instances each (15 servers total), three metrics per server (`cpu_percent`, `memory_percent`, `disk_io`), generated at 5-minute intervals over a 3-week period. `disk_io` represents throughput in MB/s

## Server type reasoning

### Web server
Handles incoming user requests and application logic.
- **CPU (business hours mean: 50)** — moderate. Real work per request, but a lot of time is spent waiting on I/O (network, database calls) rather than pure computation.
- **Memory (60)** — moderate-high. Holds session data, request/response buffers, and some application-level caching.
- **Disk I/O (100)** — low-moderate. Writes application logs per request, occasionally serves static files, but doesn't persist application data itself.

### Database server
Stores and retrieves persistent data via CRUD operations (GET/POST/UPDATE/DELETE).
- **CPU (70)** — high. Query parsing, index lookups, joins, sorting, and aggregation are genuinely CPU-intensive operations.
- **Memory (80)** — highest of all types. Databases deliberately use as much RAM as available to keep data/indexes in memory rather than reading from disk on every query — this is core to database performance.
- **Disk I/O (300)** — highest of all types. Persistent reads/writes are the database's entire job.

### Cache server
Serves frequently-accessed data from memory (RAM) to avoid hitting the database.
- **CPU (40)** — lowest of all types. Fast, simple key-value lookups require minimal computation compared to a database running complex queries.
- **Memory (80)** — high, on par with database. A cache's entire purpose is holding data in memory to avoid disk access — real caching systems (Redis, Memcached) are commonly configured to use the large majority of available RAM, since idle cache memory is wasted cache memory. This was originally set lower (50, below web server) in an earlier draft of this dataset, which contradicted the core concept of what a cache is — corrected once that inconsistency was noticed.
- **Disk I/O (50)** — low. A cache is specifically designed to avoid disk access — that's the performance win of caching in the first place. Any disk activity is typically just occasional persistence/backup snapshots, not tied to normal request handling.

### Load balancer
Sits in front of the web tier, routing incoming traffic across multiple web servers.
- **CPU (70)** — high. Routing decisions plus handling many concurrent connections can be CPU-intensive at scale, especially with SSL/TLS termination (encrypting/decrypting traffic), which many load balancers handle.
- **Memory (70)** — moderate-high. Holds connection state and session tables for many concurrent connections.
- **Disk I/O (50)** — low, same tier as cache. A load balancer routes traffic, it doesn't store data — its disk usage is limited to connection/routing logs.
- **Volatility (higher `scale` values than other types)** — because it sees the *combined* traffic of every web server at once, it reacts first and hardest to sudden traffic surges, making its metrics inherently more variable than any individual web server.

### Batch/worker node
Runs scheduled offline jobs (e.g. nightly backups, data processing, report generation) rather than responding to live user traffic.
- **Distinct pattern shape, not just magnitude** — unlike the other four types (which follow a daily business-hours cycle), the batch worker is idle (0) almost all day and spikes only during a narrow scheduled window (2–3am).
- **CPU (60), Memory (70), Disk I/O (200) during its window** — comparable to or above database, since batch jobs are often doing heavy, similarly data-intensive work (bulk reads/writes, aggregation), just concentrated into a short burst instead of spread across the day.

## Anomaly design

10 distinct anomaly events were injected across 8 of the 15 servers (some servers untouched, some with 2 events), spread across different server types so the detection model is tested on generalising across server behaviour, not just one type.

Anomalies mix two directions:
- **Spikes** — a metric jumps well above its normal baseline (e.g. web server CPU pinned near 100%)
- **Drops** — a metric falls well below its normal baseline (e.g. web server CPU near 10% during a period it should be busy)

Each injected value uses `np.random.normal(loc, scale)` rather than a flat constant, so anomalies still contain realistic noise rather than looking like an obviously synthetic flat line.

### Batch worker anomalies — a special case

Because the batch worker's normal baseline is "idle nearly all day, active only 2–3am," three distinct anomaly types were used specifically for this server type:
- **Job overran** — elevated activity *outside* the normal 2–3am window (e.g. 3:40am–6am), simulating a job that ran unusually late or long.
- **Job underperformed** — a drop *inside* the normal window (e.g. memory far below the expected ~70 during 2–2:15am), simulating a job that started but did far less work than expected.
- **Job overworked** — a spike *inside* the normal window (e.g. disk I/O far above the expected ~200), simulating a job that processed unusually large volumes of data.

This gives the batch worker meaningfully different anomaly *shapes* from the other four server types, rather than reusing the same "spike during business hours" pattern.

## Ground truth labelling

Every row includes an `is_anomaly` column (0/1), set to 1 only for rows deliberately overwritten during injection. This is not used during model training (the detection approach is unsupervised) but is used afterward to evaluate detection performance (precision/recall) against a known ground truth.

## Reproducibility

`np.random.seed(42)` is set at the top of the generation script, so re-running it produces an identical dataset every time.

## Project structure

```
├── data/               # generated CSV output
├── notebooks/          # exploratory work
├── src/                # simulate.py — the data generation pipeline
├── README.md
└── requirements.txt
```

## Run the script

Run `simulate.py` within the `src/` directory:

```
cd src
python simulate.py
```

Output is written to `../data/simulated_server_metrics.csv`.