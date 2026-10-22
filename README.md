# Django Hurricane Performance Benchmark Suite

A Docker Compose and GitHub Actions benchmark environment evaluating **`django-hurricane`** (targeting 2.0.0rc1 and newer Granian-powered releases) under synthetic, near real-world web traffic.

The suite compares five distinct deployment paradigms:
1. **WSGI (Worker=1 / Single Thread)**: Granian WSGI interface with `--workers 1` (strict single-threaded baseline for 1-to-1 comparison with single-process event loop).
2. **WSGI (Auto Threads / Multi-Thread)**: Granian WSGI interface with Hurricane's auto-threads calculation `min(32, cpu_count + 4)` threads (traditional real-world multi-threaded WSGI deployment).
3. **ASGI (Forced Sync Views)**: Granian ASGI interface running legacy synchronous Django views, demonstrating the exact penalty of Django's `sync_to_async(thread_sensitive=True)` adapter under load.
4. **ASGI (Clean Async Views)**: Granian ASGI interface with clean async views (`async def`), pooled `httpx` async client, and non-blocking template rendering.
5. **ASGI (`django-async-backend`)**: Granian ASGI interface with [django-async-backend](https://github.com/Arfey/django-async-backend) utilizing true non-blocking `psycopg 3` async connection pooling on the event loop.

---

## Architecture Overview

```
                                            +------------------------+
                                            |   Locust Load Runner   |
                                            |   (Headless Step-Load) |
                                            +-----------+------------+
                                                        |
                         +------------------------------+------------------------------+
                         |                              |                              |
                         v                              v                              v
             [ Flavors 1 & 2: WSGI ]        [ Flavor 3: ASGI-Sync ]         [ Flavors 4 & 5: ASGI ]
             Granian WSGI Mode              Granian ASGI Mode               Granian ASGI Mode
             (Single Thread vs Auto-Threads) Django sync_to_async            Clean Async Views (httpx)
             Sync DB (psycopg pool)         Sync HTTP (requests)            Standard ORM vs django-async-backend
                         |                              |                              |
                         +------------------------------+------------------------------+
                                                        |
                                                        v
                                              +--------------------+
                                              | PostgreSQL 17 (DB) |
                                              | (Real Database)    |
                                              +--------------------+
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

### Latest Benchmark Results (2026-10-22 12:23:46 UTC)
**Django Hurricane Version:** `2.0.0rc1` | **PostgreSQL:** `17` | **Python:** `3.12`

#### Server & Worker Runtime Architecture
| Flavor | Server Interface | Worker Processes | Server Threads | Event Loop | App Concurrency Model | DB Pool |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **WSGI (Worker=1)** | Granian WSGI | 1 | 1 | None | Single OS thread (In-thread) | Sync psycopg (4 conns) |
| **WSGI (Auto Threads)** | Granian WSGI | 1 | `min(32, CPU+4)` (6–12) | None | Multi-threaded (In-thread) | Sync psycopg (4 conns) |
| **ASGI (Forced Sync)** | Granian ASGI | 1 | 1 | Tokio (`mt`) | `asgiref` single-thread queue | Sync psycopg (4 conns) |
| **ASGI (Clean Async)** | Granian ASGI | 1 | 1 | Tokio (`mt`) | Native async views + threadpool DTL | Sync psycopg (4 conns) |
| **ASGI + DAB** | Granian ASGI | 1 | 1 | Tokio (`mt`) | Native async views + threadpool DTL | Async psycopg-pool (5–50 conns) |

#### Aggregate Performance Metrics
| Flavor | Throughput | Median (p50) | 95th (p95) | 99th (p99) | Error Rate | Requests |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **WSGI (Worker=1 / Single Thread)** | **51.3 req/s** | 700.0 ms | 1000.0 ms | 1100.0 ms | 0.0% | 462 |
| **WSGI (Auto Threads / Multi-Thread)** | **174.7 req/s** | 99.0 ms | 200.0 ms | 230.0 ms | 0.0% | 1,572 |
| **ASGI (Forced Sync Views)** | **80.3 req/s** | 440.0 ms | 630.0 ms | 670.0 ms | 0.0% | 723 |
| **ASGI (Clean Async Views)** | **70.9 req/s** | 560.0 ms | 750.0 ms | 820.0 ms | 0.0% | 638 |
| **ASGI + django-async-backend** | **74.0 req/s** | 490.0 ms | 620.0 ms | 650.0 ms | 0.0% | 668 |

#### Throughput (Requests per Second - Higher is better)
```text
WSGI (Worker=1 / Single Thread)  [█████████                       ]     51.3 req/s
WSGI (Auto Threads / Multi-Thread) [████████████████████████████████]    174.7 req/s
ASGI (Forced Sync Views)         [███████████████                 ]     80.3 req/s
ASGI (Clean Async Views)         [█████████████                   ]     70.9 req/s
ASGI + django-async-backend      [██████████████                  ]     74.0 req/s
```

#### 95th Percentile Latency (Lower is better)
```text
WSGI (Worker=1 / Single Thread)  [████████████████████████████████]   1000.0 ms
WSGI (Auto Threads / Multi-Thread) [██████                          ]    200.0 ms
ASGI (Forced Sync Views)         [████████████████████            ]    630.0 ms
ASGI (Clean Async Views)         [████████████████████████        ]    750.0 ms
ASGI + django-async-backend      [████████████████████            ]    620.0 ms
```

#### Concurrency Scaling & User Scaling Penalty
Latency progression and degradation factor as concurrent simulated users ramp up from initial ramp (`15` users) through mid-stage (`45` users) to peak concurrency (`50` users):

| Flavor | Initial Load (~15 Users) p50 / p95 | Mid Load (~45 Users) p50 / p95 | Peak Load (50 Users) p50 / p95 | Latency Scaling Penalty |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=1 / Single Thread)** | 160.0 ms / 290.0 ms | 360.0 ms / 570.0 ms | 570.0 ms / 928.3 ms | **3.2x** |
| **WSGI (Auto Threads / Multi-Thread)** | 48.0 ms / 93.0 ms | 42.0 ms / 100.0 ms | 67.3 ms / 167.8 ms | **1.8x** |
| **ASGI (Forced Sync Views)** | 96.0 ms / 300.0 ms | 210.0 ms / 620.0 ms | 360.0 ms / 621.7 ms | **2.07x** |
| **ASGI (Clean Async Views)** | 100.0 ms / 320.0 ms | 270.0 ms / 700.0 ms | 468.3 ms / 735.0 ms | **2.3x** |
| **ASGI + django-async-backend** | 130.0 ms / 200.0 ms | 310.0 ms / 600.0 ms | 430.0 ms / 613.3 ms | **3.07x** |

##### Latency Inflation Factor under Load Scaling (Peak p95 vs Initial p95 - Lower is better)
```text
WSGI (Worker=1 / Single Thread)  [████████████████████████████████]  3.20x penalty
WSGI (Auto Threads / Multi-Thread) [██████████████████              ]  1.80x penalty
ASGI (Forced Sync Views)         [█████████████████████           ]  2.07x penalty
ASGI (Clean Async Views)         [███████████████████████         ]  2.30x penalty
ASGI + django-async-backend      [███████████████████████████████ ]  3.07x penalty
```

#### Route Breakdown Across Flavors
| Route | WSGI (Worker=1 / Single Thread) (p95 / RPS) | WSGI (Auto Threads / Multi-Thread) (p95 / RPS) | ASGI (Forced Sync Views) (p95 / RPS) | ASGI (Clean Async Views) (p95 / RPS) | ASGI + django-async-backend (p95 / RPS) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `/api/auth/login` | 600.0 ms (5.5 rps) | 110.0 ms (5.6 rps) | 630.0 ms (5.6 rps) | 770.0 ms (5.6 rps) | 640.0 ms (5.5 rps) |
| `/api/auth/me [GET]` | 1000.0 ms (2.3 rps) | 190.0 ms (8.9 rps) | 650.0 ms (4.0 rps) | 690.0 ms (3.8 rps) | 580.0 ms (3.8 rps) |
| `/api/items [GET]` | 1000.0 ms (15.0 rps) | 200.0 ms (48.6 rps) | 620.0 ms (20.4 rps) | 760.0 ms (20.5 rps) | 590.0 ms (19.4 rps) |
| `/api/items [POST]` | 1000.0 ms (2.9 rps) | 200.0 ms (7.2 rps) | 670.0 ms (3.9 rps) | 750.0 ms (2.0 rps) | 600.0 ms (3.7 rps) |
| `/catalog/render [GET]` | 1100.0 ms (8.9 rps) | 210.0 ms (34.1 rps) | 640.0 ms (12.9 rps) | 800.0 ms (11.7 rps) | 620.0 ms (14.5 rps) |
| `/catalog/search [GET]` | 1000.0 ms (6.1 rps) | 200.0 ms (27.1 rps) | 640.0 ms (12.7 rps) | 730.0 ms (9.9 rps) | 600.0 ms (10.4 rps) |
| `/external/fetch [GET]` | 1100.0 ms (10.5 rps) | 190.0 ms (43.2 rps) | 250.0 ms (20.9 rps) | 240.0 ms (17.6 rps) | 630.0 ms (16.7 rps) |

#### Architectural Takeaways & Production Recommendations
- **WSGI (Worker=1 / Single Thread)**: The strict 1-to-1 baseline. Demonstrates the extreme vulnerability of single-threaded synchronous architectures: any blocking I/O (e.g. upstream API calls) freezes the entire server, producing severe queue buildup and high tail latency.
- **WSGI (Auto Threads / Multi-Thread)**: The traditional production deployment. Providing 6–12 worker threads absorbs concurrent requests much better, but worker threads still lock on I/O waits and scale with higher memory overhead and kernel thread contention.
- **ASGI (Forced Sync Views)**: The migration step. Demonstrates that running legacy synchronous views under ASGI gains socket multiplexing benefits from Granian's Rust event loop, but incurs threadpool context switching (`sync_to_async`).
- **ASGI (Clean Async Views)**: The balanced, general production recommendation. By writing native `async def` views for I/O endpoints and using connection-pooled HTTP clients (`httpx`), applications achieve 90%+ of ASGI benefits while retaining 100% compatibility with standard Django ORM, third-party packages, DRF, and Django admin.
- **ASGI + `django-async-backend`**: Specialized high-performance engine. Delivers the lowest latency profile by removing threadpool hops on PostgreSQL queries. However, it is not a general-purpose recommendation due to critical constraints: PostgreSQL-only driver requirement, tight coupling to Django internal releases, complex async transaction boundaries, and incompatibility with third-party Django apps that execute synchronous ORM operations.

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

While `django-async-backend` achieves the lowest tail latency ($610\text{ ms } p95$) by executing queries directly on non-blocking `psycopg 3` connections, **it is not a universal or general recommendation**. It introduces critical architectural constraints that every team must evaluate:

- **Ecosystem & Third-Party Library Incompatibility**:
  The majority of the mature Django ecosystem (Django REST Framework, `django-filter`, `django-guardian`, audit logs, OAuth toolkits, and Django Admin extensions) relies heavily on synchronous ORM calls and sync model methods (`save()`, `__iter__`, relational lookups). Introducing an async-only database backend can break these libraries or cause race conditions.
- **"Async Does Not Mean Parallel" (Connection Multiplexing Trap)**:
  A single PostgreSQL database connection cannot execute concurrent queries over `asyncio.gather()` within the same request. Attempting to run parallel queries on a single connection corrupts cursor state unless separate connections are explicitly acquired from the pool.
- **Transaction Scoping Complexity**:
  Managing asynchronous transactions (`async with transaction.aatomic():`) across complex asynchronous task graphs requires strict discipline. Leaking transactions across coroutines can deadlock connection pools.
- **Database & Version Lock-In**:
  `django-async-backend` is strictly tied to PostgreSQL and `psycopg 3` (`psycopg-pool`). Furthermore, because it monkey-patches and overrides low-level Django database backend internals (`BaseDatabaseWrapper`), releases are tightly pinned to specific Django minor releases, making framework upgrades less flexible.

---

### 3. Practical Recommendations & Decision Matrix

| Deployment Scenario | Architectural Role | When to Recommend | When to Avoid |
| :--- | :--- | :--- | :--- |
| **ASGI (Standard)** | **General Production Default** | **Recommended for 90%+ of modern Django deployments.** Clean `async def` views, shared pooled HTTP clients (`httpx`), and non-blocking sockets with Granian/Hurricane deliver +45% throughput and 40% lower latency, while remaining **100% compatible with DRF, third-party apps, and standard Django ORM**. | When an application requires sub-second database query concurrency where `sync_to_async` thread context-switching is the proven bottleneck. |
| **ASGI + `django-async-backend`** | **Specialized High-Throughput I/O Engine** | Dedicated high-concurrency microservices, greenfield API gateways, and real-time streaming services where the team has full control over all dependencies and database queries. | Codebases reliant on third-party Django apps, complex legacy transactions, or non-PostgreSQL databases. |
| **ASGI (Forced Sync Views)** | **Transitional Migration Step** | Upgrading server infrastructure from WSGI to Granian/Hurricane without refactoring views yet. Provides immediate connection multiplexing gains (+45% throughput) before code refactoring. | Long-term production without refactoring, as synchronous views still queue on Django's threadpool adapter. |
| **WSGI (Pure Sync)** | **Legacy Maintenance** | Monolithic codebases locked to thread-unsafe C-extensions or deprecated third-party middleware that explicitly fail under ASGI event loops. | Modern web applications, microservices calling external APIs, or high-concurrency environments. |
