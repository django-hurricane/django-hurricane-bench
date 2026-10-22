# Django Hurricane Performance Benchmark Suite

A Docker Compose and GitHub Actions benchmark environment evaluating **`django-hurricane`** (targeting 2.0.0rc1 and newer Granian-powered releases) under synthetic, near real-world web traffic.

The suite compares three distinct deployment paradigms:
1. **WSGI**: Granian WSGI interface with synchronous PostgreSQL and blocking HTTP operations.
2. **ASGI (Standard)**: Granian ASGI interface with standard Django ORM (queries dispatched via `sync_to_async` threadpool) and non-blocking `httpx` async calls.
3. **ASGI (`django-async-backend`)**: Granian ASGI interface with [django-async-backend](https://github.com/Arfey/django-async-backend) utilizing true non-blocking `psycopg 3` async connection pooling on the event loop.

---

## Architecture Overview

```
                                  +------------------------+
                                  |   Locust Load Runner   |
                                  |   (Headless Step-Load) |
                                  +-----------+------------+
                                              |
                     +------------------------+------------------------+
                     |                        |                        |
                     v                        v                        v
           [ Flavor 1: WSGI ]       [ Flavor 2: ASGI ]       [ Flavor 3: ASGI+DAB ]
           Granian WSGI Mode        Granian ASGI Mode        Granian ASGI Mode
           Sync DB (psycopg)        Django ASGI (Threadpool) django-async-backend (Psycopg3 Pool)
           Sync HTTP (requests)     Async HTTP (httpx)       Async HTTP (httpx)
                     |                        |                        |
                     +------------+-----------+------------------------+
                                  |                                    |
                                  v                                    v
                        +--------------------+               +--------------------+
                        | PostgreSQL 17 (DB) |               |  Fake Latency API  |
                        | (Real Database)    |               |  (min_ms, max_ms)  |
                        +--------------------+               +--------------------+
```

---

## Workload Routes

The sample Django app runs five diverse traffic paths reflecting production patterns:

| Route | Feature Area | Concurrency Characteristic |
| :--- | :--- | :--- |
| `POST /api/auth/login` | Session & Auth Middleware | Cookie signing, Session read/write, user credentials check. |
| `GET /catalog/render` | Complex Template Rendering | DTL engine overhead, nested loops, filters, context processors. |
| `GET /api/items` & `POST /api/items` | JSON API Serialization | JSON parsing, model validation, bulk query serialization. |
| `GET /external/fetch` | Unreliable Third-Party API | Interacts with `fake-api` (`/delay?min=X&max=Y`) simulating erratic upstream latency. |
| `GET /catalog/search` | Database Queries & Aggregations | Filtering, foreign key joins (`select_related`), and statistical aggregations on PostgreSQL 17. |

---

## Running Locally

### 1. Start Infrastructure & Run Full Benchmark
Execute the automated sequential benchmark runner:

```bash
# Run all flavors with default django-hurricane 2.0.0rc1
./scripts/run_benchmark.sh

# Or specify custom hurricane version and parameters:
HURRICANE_VERSION=2.0.0rc1 BENCH_USERS=200 BENCH_DURATION=60s ./scripts/run_benchmark.sh
```

### 2. Run Flavors Individually with Docker Compose
You can run any single flavor for manual testing or debugging:

```bash
# Start WSGI flavor on port 8001
docker compose --profile wsgi up -d

# Start Standard ASGI flavor on port 8002
docker compose --profile asgi up -d

# Start ASGI with django-async-backend on port 8003
docker compose --profile asgi-async up -d
```

### 3. Interactive Locust UI (Optional)
```bash
docker compose up -d postgres fake-api django-asgi
TARGET_HOST=http://localhost:8002 locust -f benchmark/locustfile.py
# Open http://localhost:8089 in your browser
```

---

## GitHub Actions Automated Benchmark

The benchmark can be triggered on GitHub Actions via **Run workflow** (`workflow_dispatch`):
- **django-hurricane version**: Inject any version from PyPI (e.g. `2.0.0rc1`).
- **Concurrent user count**: e.g., `150`, `300`, `500`.
- **Benchmark duration**: e.g., `45s`, `2m`.
- **Flavor selector**: `all`, `django-wsgi`, `django-asgi`, or `django-asgi-async`.

The GitHub Actions runner executes each flavor sequentially, writes artifact reports, and automatically updates the results section below in this `README.md`.

---

## Benchmark Results

<!-- BENCHMARK_START -->

### Latest Benchmark Results (2026-10-22 09:57:09 UTC)
**Django Hurricane Version:** `2.0.0rc1` | **PostgreSQL:** `17` | **Python:** `3.12`

| Flavor | Throughput | Median (p50) | 95th (p95) | 99th (p99) | Error Rate | Requests |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **WSGI (Granian Sync)** | **50.6 req/s** | 740.0 ms | 1300.0 ms | 1300.0 ms | 0.0% | 454 |
| **ASGI (Granian Standard Async)** | **70.9 req/s** | 580.0 ms | 730.0 ms | 770.0 ms | 0.0% | 639 |
| **ASGI + django-async-backend** | **71.0 req/s** | 500.0 ms | 600.0 ms | 660.0 ms | 0.0% | 639 |

#### Throughput (Requests per Second - Higher is better)
```text
WSGI (Granian Sync)              [███████████████████████         ]     50.6 req/s
ASGI (Granian Standard Async)    [████████████████████████████████]     70.9 req/s
ASGI + django-async-backend      [████████████████████████████████]     71.0 req/s
```

#### 95th Percentile Latency (Lower is better)
```text
WSGI (Granian Sync)              [████████████████████████████████]   1300.0 ms
ASGI (Granian Standard Async)    [██████████████████              ]    730.0 ms
ASGI + django-async-backend      [███████████████                 ]    600.0 ms
```

#### Route Breakdown Across Flavors
| Route | WSGI (Granian Sync) (p95 / RPS) | ASGI (Granian Standard Async) (p95 / RPS) | ASGI + django-async-backend (p95 / RPS) |
| :--- | :---: | :---: | :---: |
| `/api/auth/login` | 1000.0 ms (5.6 rps) | 760.0 ms (5.5 rps) | 700.0 ms (5.6 rps) |
| `/api/auth/me [GET]` | 1200.0 ms (1.8 rps) | 690.0 ms (2.8 rps) | 550.0 ms (2.9 rps) |
| `/api/items [GET]` | 1300.0 ms (12.7 rps) | 730.0 ms (19.0 rps) | 560.0 ms (19.3 rps) |
| `/api/items [POST]` | 1300.0 ms (2.8 rps) | 700.0 ms (3.6 rps) | 580.0 ms (3.0 rps) |
| `/catalog/render [GET]` | 1300.0 ms (8.4 rps) | 750.0 ms (13.3 rps) | 590.0 ms (13.6 rps) |
| `/catalog/search [GET]` | 1200.0 ms (7.9 rps) | 730.0 ms (10.2 rps) | 560.0 ms (9.0 rps) |
| `/external/fetch [GET]` | 1300.0 ms (11.5 rps) | 220.0 ms (16.5 rps) | 610.0 ms (17.7 rps) |

#### Architectural Takeaways & Recommendation
- **WSGI (Granian Sync)**: Excels on deterministic, CPU-bound workloads (like pure template rendering) but suffers severely when external dependencies (like third-party APIs or slow microservices) block worker threads, causing queue buildup.
- **ASGI (Standard)**: Resolves the worker thread starvation issue by multiplexing HTTP connections on the Granian async event loop. However, standard Django ORM calls still incur small thread-dispatch penalties via `sync_to_async`.
- **ASGI + `django-async-backend`**: Highest aggregate throughput and lowest tail latency on mixed I/O workloads. By utilizing native `psycopg3` async connections and connection pooling directly on the asyncio loop, thread hops are completely bypassed.

<!-- BENCHMARK_END -->

---

## Architectural Analysis & Practical Recommendations

### 1. WSGI (Granian Synchronous)
- **Strengths**: Predictable CPU efficiency on synchronous tasks like pure template rendering and CPU-heavy transformations.
- **Weaknesses**: Vulnerable to worker thread starvation when endpoints make external HTTP calls or wait on I/O.
- **Recommendation**: Best for traditional monoliths with minimal microservice orchestration.

### 2. ASGI (Granian Standard Async)
- **Strengths**: High resilience against slow external APIs and webhooks thanks to non-blocking socket handling on the Granian event loop.
- **Weaknesses**: Standard Django ORM operations rely on `sync_to_async` thread hops, introducing marginal latency on high-frequency DB queries.
- **Recommendation**: The go-to default for modern Django applications adopting async views, external APIs, and WebSockets.

### 3. ASGI (`django-async-backend`)
- **Strengths**: True non-blocking PostgreSQL connections via `psycopg 3` async connection pools, bypassing worker thread contention entirely.
- **Weaknesses**: Requires async-aware model workflows (`a`-methods) and careful handling of sync third-party Django apps.
- **Recommendation**: Ideal for high-concurrency API gateways, real-time microservices, and high-load Django services built on PostgreSQL 16/17.
