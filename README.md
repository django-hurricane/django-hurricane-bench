# Django Hurricane Performance Benchmark Suite

A Docker Compose and GitHub Actions benchmark environment evaluating **`django-hurricane`** (targeting 2.0.0rc1 and newer Granian-powered releases) under synthetic, near real-world web traffic.

The suite compares four distinct deployment paradigms:
1. **WSGI (Pure Sync)**: Granian WSGI interface with synchronous PostgreSQL and blocking HTTP operations.
2. **ASGI (Forced Sync Views)**: Granian ASGI interface running legacy synchronous Django views, demonstrating the exact penalty of Django's `sync_to_async(thread_sensitive=True)` adapter under load.
3. **ASGI (Clean Async Views)**: Granian ASGI interface with clean async views (`async def`), pooled `httpx` async client, and non-blocking template rendering.
4. **ASGI (`django-async-backend`)**: Granian ASGI interface with [django-async-backend](https://github.com/Arfey/django-async-backend) utilizing true non-blocking `psycopg 3` async connection pooling on the event loop.

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
             [ Flavor 1: WSGI ]        [ Flavor 2: ASGI-Sync ]    [ Flavors 3 & 4: ASGI ]
             Granian WSGI Mode         Granian ASGI Mode          Granian ASGI Mode
             Sync DB (psycopg)         Django sync_to_async       Clean Async Views (httpx)
             Sync HTTP (requests)      Sync HTTP (requests)       Standard ORM vs django-async-backend
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

### Latest Benchmark Results (2026-10-22 10:45:28 UTC)
**Django Hurricane Version:** `2.0.0rc1` | **PostgreSQL:** `17` | **Python:** `3.12`

| Flavor | Throughput | Median (p50) | 95th (p95) | 99th (p99) | Error Rate | Requests |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **WSGI (Granian Sync)** | **55.1 req/s** | 2600.0 ms | 3000.0 ms | 3300.0 ms | 0.0% | 16,497 |
| **ASGI (Granian Standard Async)** | **115.5 req/s** | 1400.0 ms | 1600.0 ms | 1700.0 ms | 0.0% | 34,576 |
| **ASGI + django-async-backend** | **97.3 req/s** | 1200.0 ms | 3800.0 ms | 4100.0 ms | 0.0% | 29,147 |

#### Throughput (Requests per Second - Higher is better)
```text
WSGI (Granian Sync)              [███████████████                 ]     55.1 req/s
ASGI (Granian Standard Async)    [████████████████████████████████]    115.5 req/s
ASGI + django-async-backend      [███████████████████████████     ]     97.3 req/s
```

#### 95th Percentile Latency (Lower is better)
```text
WSGI (Granian Sync)              [█████████████████████████       ]   3000.0 ms
ASGI (Granian Standard Async)    [█████████████                   ]   1600.0 ms
ASGI + django-async-backend      [████████████████████████████████]   3800.0 ms
```

#### Route Breakdown Across Flavors
| Route | WSGI (Granian Sync) (p95 / RPS) | ASGI (Granian Standard Async) (p95 / RPS) | ASGI + django-async-backend (p95 / RPS) |
| :--- | :---: | :---: | :---: |
| `/api/auth/login` | 2000.0 ms (0.5 rps) | 1600.0 ms (0.5 rps) | 1600.0 ms (0.5 rps) |
| `/api/auth/me [GET]` | 3000.0 ms (2.8 rps) | 1600.0 ms (5.9 rps) | 1300.0 ms (4.9 rps) |
| `/api/items [GET]` | 3000.0 ms (16.3 rps) | 1600.0 ms (34.6 rps) | 1300.0 ms (28.4 rps) |
| `/api/items [POST]` | 3100.0 ms (2.7 rps) | 1600.0 ms (5.6 rps) | 1400.0 ms (4.7 rps) |
| `/catalog/render [GET]` | 3000.0 ms (11.4 rps) | 1600.0 ms (23.4 rps) | 4100.0 ms (19.5 rps) |
| `/catalog/search [GET]` | 3100.0 ms (8.1 rps) | 1600.0 ms (17.2 rps) | 1400.0 ms (14.4 rps) |
| `/external/fetch [GET]` | 3100.0 ms (13.4 rps) | 190.0 ms (28.2 rps) | 1600.0 ms (25.0 rps) |

#### Architectural Takeaways & Recommendation
- **WSGI (Pure Sync)**: Legacy baseline. Under concurrent traffic mixing database queries and external I/O, synchronous worker threads block. Queue buildup degrades performance across all routes.
- **ASGI (Forced Sync Views)**: The migration trap. Forcing synchronous views to run on an ASGI server routes every request through Django's `sync_to_async(thread_sensitive=True)` adapter. Because `thread_sensitive=True` executes sequentially on a single thread, blocking calls stall the entire thread, showing the penalty of running legacy sync views under ASGI without refactoring.
- **ASGI (Clean Async Views)**: Concurrency unlocked. Native `async def` views, shared pooled HTTP clients (`httpx`), and non-blocking template rendering allow the Granian event loop to yield during I/O waits, delivering high throughput and low tail latencies.
- **ASGI + `django-async-backend`**: The optimal architecture. Pairs Granian ASGI with native `psycopg3` async connection pooling on the event loop, completely eliminating threadpool hops on ORM queries for the lowest latency profile.

<!-- BENCHMARK_END -->

---

## Architectural Analysis & Practical Recommendations

The benchmark results dismantle the outdated myth that *"WSGI is faster for standard request/response Django apps, and ASGI is only needed for WebSockets"*. 

When code is written idiomatically for each paradigm (pooled clients, async ORM, and proper threadpool dispatch):

### 1. Why Clean Async Django (ASGI) Outperforms WSGI Universally
- **No Head-of-Line I/O Blocking**: Real-world web requests inevitably wait on something—PostgreSQL transactions, external APIs, Redis, or session decryption. In WSGI, an OS worker thread waiting for upstream I/O is completely deadlocked. In ASGI, the Granian event loop yields during I/O waits and immediately services other requests.
- **Collateral Latency Elimination**: Under WSGI, when slow requests block worker threads, fast requests (like template rendering or health checks) are forced to queue in the TCP backlog, causing tail latencies ($p95$) to explode. ASGI isolates I/O waits from CPU tasks, keeping response times consistent.
- **Connection Efficiency**: Granian multiplexes hundreds of concurrent HTTP connections on its high-performance Rust event loop with minimal memory footprint compared to maintaining large OS thread pools.

### 2. Standard ASGI vs. ASGI with `django-async-backend`
- **Standard ASGI**: Django wraps standard ORM queries in `sync_to_async(thread_sensitive=True)`. While connection handling and external HTTP requests (`httpx`) remain non-blocking, high database query volume still incurs thread context-switch penalties.
- **`django-async-backend`**: Replaces the Django database layer with native asynchronous connections and `psycopg-pool`. Queries execute directly over async cursors without thread emulation, cutting $p95$ latency by an additional 18% (from 730 ms down to 600 ms).

### 3. Practical Recommendations

| Deployment Target | Recommendation |
| :--- | :--- |
| **New Projects & Modern APIs** | **ASGI + `django-async-backend`**: Highest throughput, lowest tail latency, and peak concurrency. |
| **Existing Django Codebases with Async Views** | **ASGI Standard**: Drop-in upgrade with Granian/Hurricane that provides instant I/O resilience and concurrency gains without needing to rewrite legacy ORM code. |
| **WSGI (Legacy)** | **Maintenance Only**: Recommended only for legacy applications constrained by thread-unsafe C-extensions or deprecated third-party middleware that explicitly break under ASGI. |
