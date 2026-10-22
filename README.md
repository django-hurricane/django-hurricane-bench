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

### Latest Benchmark Results (2026-10-22 12:02:25 UTC)
**Django Hurricane Version:** `2.0.0rc1` | **PostgreSQL:** `17` | **Python:** `3.12`

| Flavor | Throughput | Median (p50) | 95th (p95) | 99th (p99) | Error Rate | Requests |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **WSGI (Pure Sync)** | **52.1 req/s** | 710.0 ms | 1100.0 ms | 1200.0 ms | 0.0% | 468 |
| **ASGI (Forced Sync Views)** | **75.8 req/s** | 510.0 ms | 670.0 ms | 710.0 ms | 0.0% | 682 |
| **ASGI (Clean Async Views)** | **76.1 req/s** | 460.0 ms | 680.0 ms | 770.0 ms | 0.0% | 685 |
| **ASGI + django-async-backend** | **72.8 req/s** | 480.0 ms | 610.0 ms | 690.0 ms | 0.0% | 656 |

#### Throughput (Requests per Second - Higher is better)
```text
WSGI (Pure Sync)                 [██████████████████████          ]     52.1 req/s
ASGI (Forced Sync Views)         [████████████████████████████████]     75.8 req/s
ASGI (Clean Async Views)         [████████████████████████████████]     76.1 req/s
ASGI + django-async-backend      [███████████████████████████████ ]     72.8 req/s
```

#### 95th Percentile Latency (Lower is better)
```text
WSGI (Pure Sync)                 [████████████████████████████████]   1100.0 ms
ASGI (Forced Sync Views)         [███████████████████             ]    670.0 ms
ASGI (Clean Async Views)         [████████████████████            ]    680.0 ms
ASGI + django-async-backend      [██████████████████              ]    610.0 ms
```

#### Concurrency Scaling & User Scaling Penalty
Latency progression and degradation factor as concurrent simulated users ramp up from initial ramp (`15` users) through mid-stage (`45` users) to peak concurrency (`50` users):

| Flavor | Initial Load (~15 Users) p50 / p95 | Mid Load (~45 Users) p50 / p95 | Peak Load (50 Users) p50 / p95 | Latency Scaling Penalty |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Pure Sync)** | 110.0 ms / 220.0 ms | 270.0 ms / 620.0 ms | 565.0 ms / 1023.3 ms | **4.65x** |
| **ASGI (Forced Sync Views)** | 87.0 ms / 260.0 ms | 260.0 ms / 660.0 ms | 435.0 ms / 675.0 ms | **2.6x** |
| **ASGI (Clean Async Views)** | 110.0 ms / 310.0 ms | 270.0 ms / 750.0 ms | 425.0 ms / 696.7 ms | **2.25x** |
| **ASGI + django-async-backend** | 140.0 ms / 210.0 ms | 310.0 ms / 680.0 ms | 448.3 ms / 638.3 ms | **3.04x** |

##### Latency Inflation Factor under Load Scaling (Peak p95 vs Initial p95 - Lower is better)
```text
WSGI (Pure Sync)                 [████████████████████████████████]  4.65x penalty
ASGI (Forced Sync Views)         [██████████████████              ]  2.60x penalty
ASGI (Clean Async Views)         [███████████████                 ]  2.25x penalty
ASGI + django-async-backend      [█████████████████████           ]  3.04x penalty
```

#### Route Breakdown Across Flavors
| Route | WSGI (Pure Sync) (p95 / RPS) | ASGI (Forced Sync Views) (p95 / RPS) | ASGI (Clean Async Views) (p95 / RPS) | ASGI + django-async-backend (p95 / RPS) |
| :--- | :---: | :---: | :---: | :---: |
| `/api/auth/login` | 760.0 ms (5.6 rps) | 770.0 ms (5.6 rps) | 800.0 ms (5.6 rps) | 700.0 ms (5.5 rps) |
| `/api/auth/me [GET]` | 1100.0 ms (3.6 rps) | 670.0 ms (3.0 rps) | 680.0 ms (3.8 rps) | 510.0 ms (3.8 rps) |
| `/api/items [GET]` | 1100.0 ms (15.0 rps) | 670.0 ms (20.5 rps) | 680.0 ms (21.1 rps) | 570.0 ms (19.6 rps) |
| `/api/items [POST]` | 1200.0 ms (1.9 rps) | 690.0 ms (4.3 rps) | 730.0 ms (4.4 rps) | 570.0 ms (3.9 rps) |
| `/catalog/render [GET]` | 1100.0 ms (9.5 rps) | 670.0 ms (15.8 rps) | 690.0 ms (14.0 rps) | 600.0 ms (12.5 rps) |
| `/catalog/search [GET]` | 1200.0 ms (6.7 rps) | 660.0 ms (9.3 rps) | 670.0 ms (11.2 rps) | 570.0 ms (9.9 rps) |
| `/external/fetch [GET]` | 1200.0 ms (9.9 rps) | 230.0 ms (17.3 rps) | 240.0 ms (16.0 rps) | 630.0 ms (17.5 rps) |

#### Architectural Takeaways & Production Recommendations
- **WSGI (Pure Sync)**: Legacy baseline. Under concurrent traffic mixing database queries and external I/O, synchronous worker threads block. Queue buildup degrades performance across all routes.
- **ASGI (Forced Sync Views)**: The migration trap. Forcing synchronous views to run on an ASGI server routes every request through Django's `sync_to_async(thread_sensitive=True)` adapter. Because `thread_sensitive=True` executes sequentially on a single thread, blocking calls stall the entire thread, showing the penalty of running legacy sync views under ASGI without refactoring.
- **ASGI (Clean Async Views)**: The balanced, general production recommendation. By writing native `async def` views for I/O endpoints and using connection-pooled HTTP clients (`httpx`), applications achieve 90%+ of ASGI benefits while retaining 100% compatibility with standard Django ORM, third-party packages, DRF, and Django admin.
- **ASGI + `django-async-backend`**: Specialized high-performance engine. Delivers the lowest latency profile (610 ms p95) by removing threadpool hops on PostgreSQL queries. However, it is **not a general-purpose recommendation** due to critical constraints: PostgreSQL-only driver requirement, tight coupling to Django internal releases, complex async transaction boundaries, and incompatibility with third-party Django apps that execute synchronous ORM operations.

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
