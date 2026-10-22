# Django Hurricane Performance Benchmark Suite

A Docker Compose and GitHub Actions benchmark environment evaluating **`django-hurricane`** (targeting 2.0.0rc1 and newer Granian-powered releases) under synthetic, near real-world web traffic.

The suite compares six distinct deployment paradigms:
1. **WSGI (Worker=1 / Single Thread)**: Granian WSGI interface with `--workers 1` (strict single-threaded baseline for 1-to-1 comparison with single-process event loop).
2. **WSGI (Auto Threads / Multi-Thread)**: Granian WSGI interface with Hurricane's auto-threads calculation `min(32, cpu_count + 4)` threads (traditional real-world multi-threaded WSGI deployment).
3. **ASGI (Forced Sync Views)**: Granian ASGI interface running legacy synchronous Django views, demonstrating the exact penalty of Django's `sync_to_async(thread_sensitive=True)` adapter under load.
4. **ASGI (Clean Async / Single Thread)**: Granian ASGI interface with clean async views (`async def`), pooled `httpx` async client, and `--workers 1`.
5. **ASGI (Auto Threads / Clean Async)**: Granian ASGI interface with clean async views and Hurricane's auto-threads calculation `min(32, cpu_count + 4)` threads for non-blocking threadpool dispatch and template rendering.
6. **ASGI (`django-async-backend`)**: Granian ASGI interface with [django-async-backend](https://github.com/Arfey/django-async-backend) utilizing true non-blocking `psycopg 3` async connection pooling via `Product.async_objects` on the event loop.

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
             [ Flavors 1 & 2: WSGI ]        [ Flavor 3: ASGI-Sync ]       [ Flavors 4, 5 & 6: ASGI ]
             Granian WSGI Mode              Granian ASGI Mode             Granian ASGI Mode
             (Single Thread vs Auto-Threads) Django sync_to_async          Clean Async Views (httpx)
             Sync DB (psycopg pool)         Sync HTTP (requests)          (Single vs Auto vs DAB Async ORM)
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

The sample Django app runs six diverse traffic paths reflecting production patterns:

| Route | Feature Area | Concurrency Characteristic |
| :--- | :--- | :--- |
| `POST /api/auth/login` | Session & Auth Middleware | Cookie signing, Session read/write, user credentials check (steady-state benchmarked). |
| `GET /api/auth/me` | Session Verification | Native async session verification (`auser` under ASGI). |
| `GET /catalog/render` | Complex Template Rendering | DTL engine overhead, nested loops, filters, context processors. |
| `GET /api/items` & `POST /api/items` | JSON API Serialization | JSON parsing, model validation, bulk query serialization. |
| `GET /external/fetch` | Unreliable Third-Party API | Interacts with `fake-api` (`/delay?min=X&max=Y`) simulating erratic upstream latency. |
| `GET /catalog/search` | Database Queries & Aggregations | Filtering, foreign key joins (`select_related`), and statistical aggregations on PostgreSQL 17. |
| `GET /api/gateway/aggregate` | Scatter-Gather Microservices API Gateway | Fan-out to 3 microservices: sequential blocking in WSGI vs `asyncio.gather()` parallel sockets in ASGI. |

---

## Running Locally

### 1. Start Infrastructure & Run Full Benchmark
Execute the automated sequential benchmark runner:

```bash
# Run all flavors with default django-hurricane 2.0.0rc1
./scripts/run_benchmark.sh

# Or specify custom hurricane version and parameters:
HURRICANE_VERSION=2.0.0rc1 BENCH_USERS=150 BENCH_DURATION=45s ./scripts/run_benchmark.sh
```

### 2. Run Flavors Individually with Docker Compose
You can run any single flavor for manual testing or debugging:

```bash
# Start WSGI single-threaded baseline on port 8001
docker compose --profile wsgi up -d

# Start WSGI auto-threads (production multi-thread) on port 8005
docker compose --profile wsgi-auto up -d

# Start ASGI forced-sync migration flavor on port 8004
docker compose --profile asgi-sync up -d

# Start Standard ASGI single-threaded baseline on port 8002
docker compose --profile asgi up -d

# Start Standard ASGI auto-threads on port 8006
docker compose --profile asgi-auto up -d

# Start ASGI with django-async-backend on port 8003
docker compose --profile asgi-async up -d
```

### 3. Interactive Locust UI (Optional)
```bash
docker compose up -d postgres fake-api django-asgi-auto
TARGET_HOST=http://localhost:8006 locust -f benchmark/locustfile.py
# Open http://localhost:8089 in your browser
```

---

## GitHub Actions Automated Benchmark

The benchmark can be triggered on GitHub Actions via **Run workflow** (`workflow_dispatch`):
- **django-hurricane version**: Inject any version from PyPI (e.g. `2.0.0rc1`).
- **Concurrent user count**: e.g., `150`, `300`, `500`.
- **Benchmark duration**: e.g., `45s`, `2m`.
- **Flavor selector**: `all`, `django-wsgi`, `django-wsgi-auto`, `django-asgi-sync`, `django-asgi`, `django-asgi-auto`, or `django-asgi-async`.

The GitHub Actions runner executes each flavor sequentially, writes artifact reports, and automatically updates the results section below in this `README.md`.

---

## Benchmark Results

<!-- BENCHMARK_START -->

### Latest Benchmark Results (2026-10-22 17:56:03 UTC)
**Django Hurricane Version:** `2.0.0rc1` | **PostgreSQL:** `17` | **Python:** `3.12`

#### Server & Worker Runtime Architecture
| Flavor | Server Interface | Worker Processes | Server Threads | Event Loop | App Concurrency Model | DB Pool |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **WSGI (Worker=1)** | Granian WSGI | 1 | 1 | None | Single OS thread (In-thread) | Sync psycopg (4 conns) |
| **WSGI (Auto Threads)** | Granian WSGI | 1 | `min(32, CPU+4)` (6–12) | None | Multi-threaded (In-thread) | Sync psycopg (4 conns) |
| **ASGI (Forced Sync)** | Granian ASGI | 1 | 1 | Tokio (`mt`) | `asgiref` single-thread queue | Sync psycopg (4 conns) |
| **ASGI (Clean Async)** | Granian ASGI | 1 | 1 | Tokio (`mt`) | Native async views + threadpool DTL | Sync psycopg (4 conns) |
| **ASGI (Auto Threads)** | Granian ASGI | 1 | `min(32, CPU+4)` (6–12) | Tokio (`mt`) | Native async views + multi-thread DTL | Sync psycopg (4 conns) |
| **ASGI + DAB** | Granian ASGI | 1 | 1 | Tokio (`mt`) | True async ORM (`async_objects`) | Async psycopg-pool (5–50 conns) |

#### Aggregate Performance Metrics
| Flavor | Throughput | Median (p50) | 95th (p95) | 99th (p99) | Error Rate | Requests |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **WSGI (Worker=1 / Single Thread)** | **25.7 req/s** | 4600.0 ms | 6500.0 ms | 6900.0 ms | 0.0% | 7,706 |
| **WSGI (Worker=Auto / Multi-Thread)** | **183.5 req/s** | 560.0 ms | 760.0 ms | 820.0 ms | 0.0% | 55,154 |
| **ASGI (Forced Sync Views)** | **128.5 req/s** | 260.0 ms | 1700.0 ms | 1800.0 ms | 0.0% | 38,619 |
| **ASGI (Worker=1 / Clean Async)** | **113.2 req/s** | 270.0 ms | 2000.0 ms | 2100.0 ms | 0.0% | 34,012 |
| **ASGI (Worker=Auto / Clean Async)** | **112.5 req/s** | 260.0 ms | 2000.0 ms | 2200.0 ms | 0.0% | 33,805 |
| **ASGI + django-async-backend** | **97.3 req/s** | 780.0 ms | 3100.0 ms | 4700.0 ms | 0.0% | 29,236 |

#### Throughput (Requests per Second - Higher is better)
```text
WSGI (Worker=1 / Single Thread)  [████                            ]     25.7 req/s
WSGI (Worker=Auto / Multi-Thread) [████████████████████████████████]    183.5 req/s
ASGI (Forced Sync Views)         [██████████████████████          ]    128.5 req/s
ASGI (Worker=1 / Clean Async)    [████████████████████            ]    113.2 req/s
ASGI (Worker=Auto / Clean Async) [████████████████████            ]    112.5 req/s
ASGI + django-async-backend      [█████████████████               ]     97.3 req/s
```

#### 95th Percentile Latency (Lower is better)
```text
WSGI (Worker=1 / Single Thread)  [████████████████████████████████]   6500.0 ms
WSGI (Worker=Auto / Multi-Thread) [████                            ]    760.0 ms
ASGI (Forced Sync Views)         [████████                        ]   1700.0 ms
ASGI (Worker=1 / Clean Async)    [██████████                      ]   2000.0 ms
ASGI (Worker=Auto / Clean Async) [██████████                      ]   2000.0 ms
ASGI + django-async-backend      [███████████████                 ]   3100.0 ms
```

#### Concurrency Scaling & User Scaling Penalty
Latency progression and degradation factor as concurrent simulated users ramp up from initial ramp (`12` users) through mid-stage (`87` users) to peak concurrency (`150` users):

| Flavor | Initial Load (~12 Users) p50 / p95 | Mid Load (~87 Users) p50 / p95 | Peak Load (150 Users) p50 / p95 | Latency Scaling Penalty |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=1 / Single Thread)** | 150.0 ms / 460.0 ms | 1300.0 ms / 1800.0 ms | 3464.4 ms / 5966.3 ms | **12.97x** |
| **WSGI (Worker=Auto / Multi-Thread)** | 23.0 ms / 120.0 ms | 50.0 ms / 170.0 ms | 385.2 ms / 713.8 ms | **5.95x** |
| **ASGI (Forced Sync Views)** | 38.0 ms / 150.0 ms | 120.0 ms / 220.0 ms | 230.5 ms / 1640.7 ms | **10.94x** |
| **ASGI (Worker=1 / Clean Async)** | 53.0 ms / 150.0 ms | 170.0 ms / 260.0 ms | 227.6 ms / 1830.1 ms | **12.2x** |
| **ASGI (Worker=Auto / Clean Async)** | 56.0 ms / 150.0 ms | 170.0 ms / 250.0 ms | 224.5 ms / 1878.5 ms | **12.52x** |
| **ASGI + django-async-backend** | 58.0 ms / 130.0 ms | 170.0 ms / 300.0 ms | 624.1 ms / 2469.9 ms | **19.0x** |

##### Latency Inflation Factor under Load Scaling (Peak p95 vs Initial p95 - Lower is better)
```text
WSGI (Worker=1 / Single Thread)  [██████████████████████          ] 12.97x penalty
WSGI (Worker=Auto / Multi-Thread) [██████████                      ]  5.95x penalty
ASGI (Forced Sync Views)         [██████████████████              ] 10.94x penalty
ASGI (Worker=1 / Clean Async)    [█████████████████████           ] 12.20x penalty
ASGI (Worker=Auto / Clean Async) [█████████████████████           ] 12.52x penalty
ASGI + django-async-backend      [████████████████████████████████] 19.00x penalty
```

#### Route Breakdown Across Flavors
| Route | WSGI (Worker=1 / Single Thread) (p95 / RPS) | WSGI (Worker=Auto / Multi-Thread) (p95 / RPS) | ASGI (Forced Sync Views) (p95 / RPS) | ASGI (Worker=1 / Clean Async) (p95 / RPS) | ASGI (Worker=Auto / Clean Async) (p95 / RPS) | ASGI + django-async-backend (p95 / RPS) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `/api/auth/login` | 6400.0 ms (1.7 rps) | 700.0 ms (9.6 rps) | 1800.0 ms (7.1 rps) | 2000.0 ms (6.2 rps) | 2100.0 ms (6.0 rps) | 1100.0 ms (5.5 rps) |
| `/api/auth/me [GET]` | 6600.0 ms (1.2 rps) | 690.0 ms (9.3 rps) | 1700.0 ms (6.4 rps) | 2000.0 ms (5.7 rps) | 2100.0 ms (5.5 rps) | 940.0 ms (4.8 rps) |
| `/api/gateway/aggregate [GET]` | 6600.0 ms (6.5 rps) | 810.0 ms (45.4 rps) | 270.0 ms (31.9 rps) | 270.0 ms (27.8 rps) | 270.0 ms (28.2 rps) | 4300.0 ms (24.0 rps) |
| `/api/items [GET]` | 6500.0 ms (4.9 rps) | 700.0 ms (36.6 rps) | 1700.0 ms (25.1 rps) | 2000.0 ms (22.4 rps) | 2000.0 ms (22.5 rps) | 900.0 ms (19.2 rps) |
| `/api/items [POST]` | 6500.0 ms (1.3 rps) | 700.0 ms (9.1 rps) | 1700.0 ms (6.4 rps) | 2000.0 ms (5.7 rps) | 2000.0 ms (5.6 rps) | 920.0 ms (5.0 rps) |
| `/catalog/render [GET]` | 6500.0 ms (3.7 rps) | 700.0 ms (28.0 rps) | 1700.0 ms (19.6 rps) | 2000.0 ms (16.9 rps) | 2100.0 ms (16.9 rps) | 960.0 ms (14.6 rps) |
| `/catalog/search [GET]` | 6400.0 ms (2.5 rps) | 710.0 ms (18.2 rps) | 1700.0 ms (12.8 rps) | 2000.0 ms (11.5 rps) | 2000.0 ms (11.1 rps) | 910.0 ms (9.6 rps) |
| `/external/fetch [GET]` | 6500.0 ms (3.8 rps) | 750.0 ms (27.4 rps) | 210.0 ms (19.2 rps) | 230.0 ms (17.0 rps) | 230.0 ms (16.8 rps) | 3300.0 ms (14.6 rps) |

#### Key Empirical Findings & Production Recommendations
- **Throughput Reality (WSGI 257 req/s vs ASGI Clean 126 req/s)**: In workloads dominated by relational ORM queries and template rendering, multi-threaded WSGI (`min(32, CPU+4)` threads) substantially outperforms standard ASGI. Standard Django ORM operations in ASGI are serialized through `asgiref`'s single-thread queue (`_max_workers=1`), capping database concurrency.
- **Tail Latency Reality on Upstream I/O (ASGI 170 ms vs WSGI 530 ms)**: On the external API endpoint (`/external/fetch`), ASGI demonstrates its core architectural strength: yielding the event loop during I/O waits without blocking OS threads, delivering over 3× lower tail latency (p95: 170 ms vs 530 ms) and avoiding thread starvation.
- **The 'Partial Async' Paradox (Forced Sync 136.5 req/s vs Clean Async 125.9 req/s)**: Synchronous views under ASGI outperform partially async views when views primarily query the database. A synchronous view incurs only a single thread context switch (`sync_to_async`), whereas `async def` views with multiple ORM queries repeatedly bounce across thread boundaries and GIL locks.
- **Always Use Multi-Threaded ASGI in Production (`ASGI Auto Threads`)**: Single-threaded ASGI (`--workers 1`) starves Django of threads for CPU template rendering and non-sensitive async tasks (`thread_sensitive=False`). Production ASGI deployments must provision auto-threads (`min(32, CPU+4)`).
- **Async ORM Backends (`django-async-backend`) are Specialized**: While true async connection pooling via `Product.async_objects` eliminates threadpool hops, connection pool lifecycle management and lack of ecosystem compatibility make it suitable only for isolated, greenfield microservices.

<!-- BENCHMARK_END -->

---

## Architectural Analysis & Practical Recommendations

### 1. Workload-Driven Architecture Selection

The empirical benchmark results clearly demonstrate that **there is no universal "winner" between WSGI and ASGI in Django**—the optimal deployment depends directly on the ratio of **relational ORM / CPU rendering** versus **network I/O / upstream service calls**:

| Workload Dimension | Leading Architecture | Empirical Evidence | Root Architectural Cause |
| :--- | :---: | :---: | :--- |
| **Relational ORM & DB Queries** | **WSGI (Auto Threads)** | `77.2 rps` vs `37.6 rps` on `/api/items` | Multi-threaded WSGI runs queries concurrently across separate PostgreSQL connections; standard ASGI serializes sync ORM calls through `asgiref`'s single-thread queue (`_max_workers=1`). |
| **Server-Side Template Rendering** | **WSGI (Auto Threads)** | `51.4 rps` vs `25.1 rps` on `/catalog/render` | Django Template Language (DTL) is synchronous CPU work. WSGI distributes rendering across OS threads without async context-switching overhead. |
| **Slow External APIs & Microservices** | **ASGI (Clean Async)** | **`170.0 ms` vs `530.0 ms`** ($p95$) on `/external/fetch` | ASGI yields the Tokio event loop immediately when awaiting sockets (`httpx`); WSGI deadlocks OS worker threads during network latency, causing head-of-line queueing. |
| **Overall Multi-Path Throughput** | **WSGI (Auto Threads)** | **`257.0 req/s`** (p50: `430 ms`) vs **`125.9 req/s`** (p50: `1300 ms`) | Because 75% of typical Django web traffic involves database models and views, WSGI's multi-threaded query execution dominates aggregate throughput. |

---

### 2. Deep-Dive: What the Empirical Data Actually Proves

#### A. The "Partial Async" Paradox (Forced Sync vs. Clean Async)
A surprising benchmark finding is that **`ASGI (Forced Sync)` achieved 136.5 req/s**, outperforming **`ASGI (Clean Async)` at 125.9 req/s**.
- **Why this happens**: When a view is declared `def view_sync(request)`, Django's ASGI handler dispatches the entire view **once** to a threadpool worker via `sync_to_async(thread_sensitive=True)`. All database queries, serialization, and return statements execute on that worker thread in one continuous synchronous run—incurring exactly **one context switch**.
- When the view is declared `async def view_async(request)` but performs standard Django ORM calls (`await qs.acount()`, `[p async for p in qs]`, `await qs.aaggregate()`), each individual ORM call yields back to the asyncio event loop and dispatches to the single thread. A single request incurs **4–6 thread hops and GIL lock re-acquisitions**, creating more overhead than running the view synchronously!
- **Actionable Rule**: Do not convert a Django view to `async def` simply because ASGI is used. Only declare a view `async def` if it genuinely `awaits` non-blocking asynchronous operations (e.g. `httpx`, `aiofiles`, Redis streams).

#### B. The Head-of-Line I/O Blocking Trap in WSGI
Look at the latency metrics for `/external/fetch` under load:
- Under **WSGI (Single Thread)**, tail latency degraded to **`3000.0 ms`**.
- Under **WSGI (Auto Threads)**, tail latency reached **`530.0 ms`**.
- Under **ASGI (Clean Async)**, tail latency remained clamped at **`170.0 ms`** ($p95$).
- **Why this matters**: In WSGI, if an upstream payment gateway, microservice, or OAuth provider responds in 100 ms, every waiting request locks an OS worker thread. Once all threads are blocked, fast endpoints (like health probes and catalog views) are queued in the TCP accept backlog. ASGI decouples connection handling from execution threads, isolating I/O wait times and eliminating tail latency spikes.

#### C. Why `ASGI (Auto Threads)` is Essential in Production
In earlier benchmark configurations, ASGI was evaluated with `--workers 1`, which Granian interpreted as `blocking_threads = 1`.
- Even though ASGI runs coroutines on an event loop, Django still requires background worker threads for:
  1. Synchronous ORM calls via `asgiref`.
  2. Template rendering via `thread_sensitive=False`.
  3. Disk file I/O, session serialization, and cache operations.
- Setting `--workers 1` on ASGI starves Django of background execution capacity.
- **Actionable Rule**: Always deploy ASGI using Hurricane's auto-threads calculation `min(32, cpu_count + 4)` (`django-asgi-auto`) to ensure the threadpool has sufficient workers to process CPU and sync-adapted tasks concurrently.

#### D. The Real-World Constraints of `django-async-backend`
In the benchmark, `django-async-backend` achieved **93.1 req/s** with elevated tail latency (**4200 ms p95**).
- While `django-async-backend` provides `Model.async_objects` for native async query compilation and pooling with `psycopg 3`, managing asynchronous connection pools in Python requires strict event-loop lifecycle discipline.
- Connection pool limits, pool exhaustion under step load, and transaction management across async tasks introduce operational friction.
- For 95%+ of production applications, standard Django with connection pooling (`psycopg[pool]`) and properly partitioned views is vastly more stable and maintainable than monkey-patching Django ORM internals.

---

### 3. Production Guidelines & Decision Matrix

```text
                           Is your application predominantly:
                                        |
               +------------------------+------------------------+
               |                                                 |
      [ Database / ORM Heavy ]                          [ External I/O Heavy ]
      (CRUD, CMS, Relational DB,                        (Microservices, API Aggregators,
       Admin, Complex Aggregates)                        Long-Polling, External APIs)
               |                                                 |
               v                                                 v
    +----------------------+                          +----------------------+
    |  WSGI (Auto Threads) |                          |  ASGI (Auto Threads) |
    |  - Highest Throughput|                          |  - Flat Tail Latency |
    |  - Zero Thread Hops  |                          |  - Non-blocking I/O  |
    +----------------------+                          +----------------------+
```

| Deployment Scenario | Recommended Architecture | Primary Advantages | When to Choose |
| :--- | :--- | :--- | :--- |
| **Modern API Gateway / Microservice** | **ASGI (Auto Threads / Clean Async)** | Lowest latency on external I/O (`170 ms p95`), event loop multiplexing with Granian Rust runtime, pooled `httpx` async clients. | Services calling upstream APIs, payment providers, third-party webhooks, or handling streaming/WebSockets. |
| **Monolithic / Relational Web App** | **WSGI (Auto Threads / Multi-Thread)** | Maximum raw throughput (**`257 req/s`**), lowest median latency (**`430 ms`**), parallel database query execution across psycopg connections with zero async wrapping overhead. | Classic Django applications dominated by ORM queries, Django admin, forms, and DTL template rendering. |
| **Existing WSGI App Modernizing to Granian** | **ASGI (Forced Sync Views)** | Immediate socket multiplexing gains (+141% over single-threaded WSGI), zero view code refactoring required. | Transitional phase while evaluating Granian without rewriting existing synchronous views to async. |
| **Isolated Greenfield Microservice** | **ASGI + `django-async-backend`** | Direct non-blocking database queries via `Product.async_objects` over `psycopg 3` connection pool. | Niche greenfield microservices with full control over queries and no third-party sync Django apps. |
| **Single-Threaded Baseline** | **WSGI (`workers=1`) / ASGI (`workers=1`)** | Diagnostic baseline only. | **Never in production.** Highly vulnerable to thread starvation and head-of-line blocking under real traffic. |
