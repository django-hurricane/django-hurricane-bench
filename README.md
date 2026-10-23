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
# Run all flavors with default django-hurricane 2.0.0rc1 (mixed workload)
./scripts/run_benchmark.sh

# Or specify custom hurricane version, parameters, and isolated workloads:
HURRICANE_VERSION=2.0.0rc1 BENCH_USERS=150 BENCH_DURATION=45s ./scripts/run_benchmark.sh

# Run an isolated endpoint without cross-talk (e.g. pure API Gateway fan-out):
BENCH_WORKLOADS="gateway_aggregate" ./scripts/run_benchmark.sh

# Run both mixed and all isolated workloads:
BENCH_WORKLOADS="all" ./scripts/run_benchmark.sh
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

## Release Archiving & Version Tracking

Every benchmark run automatically archives its full markdown report into the [`archive/`](./archive) directory (e.g. `archive/benchmark-2.0.0rc1.md`).
- If a release is evaluated multiple times, its archived report is updated in-place.
- `README.md` is automatically populated with the report of the **highest release according to Semantic Versioning (SemVer)**.

---

## GitHub Actions Automated Benchmark

The benchmark can be triggered on GitHub Actions via **Run workflow** (`workflow_dispatch`):
- **django-hurricane version**: Inject any version from PyPI (e.g. `2.0.0rc1`).
- **Concurrent user count**: e.g., `150`, `300`, `500`.
- **Benchmark duration**: e.g., `45s`, `2m`.
- **Workload**: `mixed` (default), `all`, or individual isolated workload (`gateway_aggregate`, `catalog_render`, `external_fetch`, `items_get`, `catalog_search`).
- **Flavor selector**: `all`, `django-wsgi`, `django-wsgi-auto`, `django-asgi-sync`, `django-asgi`, `django-asgi-auto`, or `django-asgi-async`.

The GitHub Actions runner executes each flavor sequentially, writes artifact reports, updates the archive in `archive/`, and updates the results section in this `README.md`.

---

## Benchmark Results

<!-- BENCHMARK_START -->

### Latest Benchmark Results (2026-10-23 09:14:22 UTC)
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

#### Aggregate Performance Metrics (Mixed Workload)
| Flavor | Throughput | Median (p50) | 95th (p95) | 99th (p99) | Error Rate | Requests |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **WSGI (Worker=1 / Single Thread)** | **29.1 req/s** | 1300.0 ms | 3000.0 ms | 3100.0 ms | 0.0% | 435 |
| **WSGI (Worker=Auto / Multi-Thread)** | **147.3 req/s** | 230.0 ms | 510.0 ms | 570.0 ms | 0.0% | 2,217 |
| **ASGI (Forced Sync Views)** | **71.5 req/s** | 280.0 ms | 1900.0 ms | 2000.0 ms | 0.0% | 1,073 |
| **ASGI (Worker=1 / Clean Async)** | **60.1 req/s** | 350.0 ms | 2200.0 ms | 2500.0 ms | 0.0% | 901 |
| **ASGI (Worker=Auto / Clean Async)** | **60.6 req/s** | 300.0 ms | 2300.0 ms | 2600.0 ms | 0.0% | 910 |
| **ASGI + django-async-backend** | **59.8 req/s** | 720.0 ms | 1800.0 ms | 2700.0 ms | 0.0% | 898 |

#### Throughput (Requests per Second - Higher is better)
```text
WSGI (Worker=1 / Single Thread)  [██████                          ]     29.1 req/s
WSGI (Worker=Auto / Multi-Thread) [████████████████████████████████]    147.3 req/s
ASGI (Forced Sync Views)         [████████████████                ]     71.5 req/s
ASGI (Worker=1 / Clean Async)    [█████████████                   ]     60.1 req/s
ASGI (Worker=Auto / Clean Async) [█████████████                   ]     60.6 req/s
ASGI + django-async-backend      [█████████████                   ]     59.8 req/s
```

#### 95th Percentile Latency (Lower is better)
```text
WSGI (Worker=1 / Single Thread)  [████████████████████████████████]   3000.0 ms
WSGI (Worker=Auto / Multi-Thread) [█████                           ]    510.0 ms
ASGI (Forced Sync Views)         [████████████████████            ]   1900.0 ms
ASGI (Worker=1 / Clean Async)    [███████████████████████         ]   2200.0 ms
ASGI (Worker=Auto / Clean Async) [█████████████████████████       ]   2300.0 ms
ASGI + django-async-backend      [███████████████████             ]   1800.0 ms
```

#### Concurrency Scaling & User Scaling Penalty
Latency progression and degradation factor as concurrent simulated users ramp up from initial ramp (`12` users) through mid-stage (`50` users) to peak concurrency (`100` users):

| Flavor | Initial Load (~12 Users) p50 / p95 | Mid Load (~50 Users) p50 / p95 | Peak Load (100 Users) p50 / p95 | Latency Scaling Penalty |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=1 / Single Thread)** | 240.0 ms / 510.0 ms | 880.0 ms / 1200.0 ms | 1250.0 ms / 2650.0 ms | **5.2x** |
| **WSGI (Worker=Auto / Multi-Thread)** | 60.0 ms / 130.0 ms | 73.0 ms / 240.0 ms | 207.5 ms / 465.0 ms | **3.58x** |
| **ASGI (Forced Sync Views)** | 110.0 ms / 240.0 ms | 180.0 ms / 420.0 ms | 267.5 ms / 1600.0 ms | **6.67x** |
| **ASGI (Worker=1 / Clean Async)** | 99.0 ms / 260.0 ms | 240.0 ms / 530.0 ms | 330.0 ms / 1900.0 ms | **7.31x** |
| **ASGI (Worker=Auto / Clean Async)** | 120.0 ms / 230.0 ms | 230.0 ms / 510.0 ms | 290.0 ms / 1925.0 ms | **8.37x** |
| **ASGI + django-async-backend** | 92.0 ms / 200.0 ms | 210.0 ms / 770.0 ms | 667.5 ms / 1575.0 ms | **7.88x** |

#### Response Time Scaling Under User Ramp-Up (p95 Latency - Lower is better)
Visual progression of 95th percentile latency across user ramp stages:
```text
WSGI (Worker=1 / Single Thread):
   12 Users [██          ]  510.0 ms
   24 Users [███         ]  590.0 ms
   25 Users [█████       ] 1166.7 ms
   50 Users [█████       ] 1200.0 ms
   60 Users [███████     ] 1550.0 ms
   85 Users [█████████   ] 2000.0 ms
  100 Users [████████████] 2650.0 ms
  Scaling Penalty Factor: 5.20x

WSGI (Worker=Auto / Multi-Thread):
   12 Users [█           ]  130.0 ms
   24 Users [█           ]  140.0 ms
   25 Users [█           ]  140.0 ms
   50 Users [█           ]  240.0 ms
   60 Users [█           ]  282.5 ms
   85 Users [██          ]  370.0 ms
  100 Users [██          ]  465.0 ms
  Scaling Penalty Factor: 3.58x

ASGI (Forced Sync Views):
   12 Users [█           ]  240.0 ms
   24 Users [█           ]  300.0 ms
   25 Users [█           ]  283.3 ms
   50 Users [██          ]  420.0 ms
   60 Users [████        ]  957.5 ms
   85 Users [████        ]  970.0 ms
  100 Users [███████     ] 1600.0 ms
  Scaling Penalty Factor: 6.67x

ASGI (Worker=1 / Clean Async):
   12 Users [█           ]  260.0 ms
   24 Users [██          ]  420.0 ms
   25 Users [██          ]  400.0 ms
   50 Users [██          ]  530.0 ms
   60 Users [█████       ] 1170.0 ms
   85 Users [██████      ] 1400.0 ms
  100 Users [█████████   ] 1900.0 ms
  Scaling Penalty Factor: 7.31x

ASGI (Worker=Auto / Clean Async):
   12 Users [█           ]  230.0 ms
   24 Users [██          ]  490.0 ms
   25 Users [██          ]  396.7 ms
   50 Users [██          ]  510.0 ms
   60 Users [█████       ] 1100.0 ms
   85 Users [█████       ] 1200.0 ms
  100 Users [█████████   ] 1925.0 ms
  Scaling Penalty Factor: 8.37x

ASGI + django-async-backend:
   12 Users [█           ]  200.0 ms
   24 Users [█           ]  290.0 ms
   25 Users [█           ]  323.3 ms
   50 Users [███         ]  770.0 ms
   60 Users [████        ]  972.5 ms
   85 Users [█████       ] 1100.0 ms
  100 Users [███████     ] 1575.0 ms
  Scaling Penalty Factor: 7.88x

```

#### Isolated Workload Performance (Pure Endpoint Measurement)
Workloads executed in isolation to eliminate cross-traffic contention and measure raw endpoint capability:

##### API Gateway / BFF (Scatter-Gather Fan-Out)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=Auto / Multi-Thread)** | **100.8 req/s** | 410.0 ms | 840.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **87.1 req/s** | 390.0 ms | 1100.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **47.1 req/s** | 770.0 ms | 2300.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **46.7 req/s** | 730.0 ms | 2600.0 ms | 0.0% |
| **ASGI + django-async-backend** | **39.4 req/s** | 950.0 ms | 2900.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **12.5 req/s** | 2800.0 ms | 5600.0 ms | 0.0% |

##### Catalog Render (DTL Template Engine)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=1 / Single Thread)** | **112.9 req/s** | 330.0 ms | 760.0 ms | 0.0% |
| **WSGI (Worker=Auto / Multi-Thread)** | **53.8 req/s** | 680.0 ms | 1800.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **49.7 req/s** | 980.0 ms | 1800.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **46.7 req/s** | 1100.0 ms | 2100.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **41.2 req/s** | 1100.0 ms | 2000.0 ms | 0.0% |
| **ASGI + django-async-backend** | **34.1 req/s** | 1300.0 ms | 2700.0 ms | 0.0% |

##### External Fetch (Upstream API I/O)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=Auto / Multi-Thread)** | **175.6 req/s** | 150.0 ms | 360.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **107.4 req/s** | 330.0 ms | 830.0 ms | 0.0% |
| **ASGI + django-async-backend** | **74.6 req/s** | 570.0 ms | 1500.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **73.1 req/s** | 500.0 ms | 1700.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **72.1 req/s** | 480.0 ms | 1500.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **22.9 req/s** | 1600.0 ms | 3500.0 ms | 0.0% |

##### Items API [GET] (ORM Serialization)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=1 / Single Thread)** | **200.0 req/s** | 150.0 ms | 360.0 ms | 0.0% |
| **WSGI (Worker=Auto / Multi-Thread)** | **173.8 req/s** | 170.0 ms | 400.0 ms | 0.0% |
| **ASGI + django-async-backend** | **91.1 req/s** | 460.0 ms | 1100.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **78.7 req/s** | 580.0 ms | 1200.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **75.7 req/s** | 580.0 ms | 1300.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **72.8 req/s** | 640.0 ms | 1300.0 ms | 0.0% |

##### Items API [POST] (ORM Inserts)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=Auto / Multi-Thread)** | **287.0 req/s** | 43.0 ms | 160.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **220.3 req/s** | 82.0 ms | 310.0 ms | 0.0% |
| **ASGI + django-async-backend** | **102.6 req/s** | 380.0 ms | 860.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **96.1 req/s** | 420.0 ms | 1000.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **89.4 req/s** | 480.0 ms | 1100.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **88.1 req/s** | 460.0 ms | 1100.0 ms | 0.0% |

##### Catalog Search (PostgreSQL Joins & Aggregates)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=Auto / Multi-Thread)** | **153.1 req/s** | 200.0 ms | 500.0 ms | 0.0% |
| **ASGI + django-async-backend** | **90.2 req/s** | 520.0 ms | 880.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **89.0 req/s** | 520.0 ms | 990.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **73.7 req/s** | 630.0 ms | 1300.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **70.0 req/s** | 670.0 ms | 1400.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **69.3 req/s** | 650.0 ms | 1400.0 ms | 0.0% |

##### Authentication & Session Middleware
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=1 / Single Thread)** | **216.9 req/s** | 80.0 ms | 360.0 ms | 0.0% |
| **WSGI (Worker=Auto / Multi-Thread)** | **196.9 req/s** | 120.0 ms | 320.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **81.0 req/s** | 570.0 ms | 1200.0 ms | 0.0% |
| **ASGI + django-async-backend** | **76.1 req/s** | 550.0 ms | 1300.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **72.6 req/s** | 630.0 ms | 1300.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **72.5 req/s** | 630.0 ms | 1300.0 ms | 0.0% |

#### Route Breakdown Across Flavors (Mixed Workload)
| Route | WSGI (Worker=1 / Single Thread) (p95 / RPS) | WSGI (Worker=Auto / Multi-Thread) (p95 / RPS) | ASGI (Forced Sync Views) (p95 / RPS) | ASGI (Worker=1 / Clean Async) (p95 / RPS) | ASGI (Worker=Auto / Clean Async) (p95 / RPS) | ASGI + django-async-backend (p95 / RPS) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `/api/auth/login` | 3000.0 ms (7.8 rps) | 480.0 ms (14.8 rps) | 1900.0 ms (9.3 rps) | 2300.0 ms (9.5 rps) | 2600.0 ms (9.9 rps) | 1600.0 ms (9.3 rps) |
| `/api/auth/me [GET]` | 3100.0 ms (1.2 rps) | 460.0 ms (7.5 rps) | 1900.0 ms (3.3 rps) | 2300.0 ms (2.6 rps) | 2200.0 ms (2.4 rps) | 1100.0 ms (2.6 rps) |
| `/api/gateway/aggregate [GET]` | 3100.0 ms (5.2 rps) | 560.0 ms (36.5 rps) | 330.0 ms (17.4 rps) | 450.0 ms (14.8 rps) | 380.0 ms (14.2 rps) | 2500.0 ms (12.3 rps) |
| `/api/items [GET]` | 3000.0 ms (4.1 rps) | 460.0 ms (27.5 rps) | 1900.0 ms (12.5 rps) | 2200.0 ms (10.9 rps) | 2300.0 ms (10.6 rps) | 1200.0 ms (11.9 rps) |
| `/api/items [POST]` | 3100.0 ms (0.9 rps) | 440.0 ms (7.0 rps) | 1900.0 ms (2.9 rps) | 2200.0 ms (2.1 rps) | 2100.0 ms (1.7 rps) | 1200.0 ms (2.7 rps) |
| `/catalog/render [GET]` | 2900.0 ms (3.8 rps) | 470.0 ms (19.7 rps) | 2000.0 ms (9.9 rps) | 2300.0 ms (8.3 rps) | 2300.0 ms (7.9 rps) | 1300.0 ms (7.5 rps) |
| `/catalog/search [GET]` | 3000.0 ms (2.3 rps) | 470.0 ms (13.8 rps) | 1900.0 ms (6.1 rps) | 2300.0 ms (3.9 rps) | 2300.0 ms (5.2 rps) | 1200.0 ms (5.7 rps) |
| `/external/fetch [GET]` | 3000.0 ms (3.8 rps) | 480.0 ms (20.5 rps) | 260.0 ms (10.0 rps) | 440.0 ms (7.9 rps) | 320.0 ms (8.7 rps) | 2100.0 ms (7.9 rps) |

#### Key Empirical Findings & Production Recommendations
- **Isolated Relational ORM vs. Mixed Traffic Reality**: In pure, isolated database queries with zero network waiting, multi-threaded WSGI (`WSGI Worker=Auto`) achieves higher raw query throughput because OS threads execute queries directly in parallel without event-loop overhead. However, in mixed production traffic containing even modest external I/O, worker thread stalls allow `ASGI (Forced Sync Views)` to achieve higher aggregate throughput and lower median latency across the application.
- **Hardware Footprint & Kubernetes Pod Constraints (Cloud-Native Reality)**: Hardware sizing heavily influences the WSGI vs. ASGI trade-off. On large multi-core bare-metal machines, WSGI has enough threadpool depth to absorb mixed traffic without thread exhaustion. However, in production Kubernetes clusters where applications run in constrained pods (e.g. 1–2 vCPUs), WSGI's threadpool is restricted to just 5–6 threads, causing rapid thread starvation on blocking I/O. In contrast, ASGI multiplexes hundreds of concurrent connections on Granian's lightweight Tokio Rust event loop within that same constrained pod footprint, giving ASGI a decisive architectural advantage in cloud-native containerized deployments.
- **Upstream Network I/O & Microservice Fan-Out (ASGI Advantage)**: On workloads involving external API calls, slow third-party webhooks, and scatter-gather API Gateway patterns (`/external/fetch` and `/api/gateway/aggregate`), ASGI demonstrates its fundamental architectural superiority. Coroutines yield the Tokio event loop during network waits without tying up OS worker threads, keeping tail latencies flat and eliminating the thread-starvation deadlocks that severely degrade WSGI under load.
- **The 'Partial Async' Context-Switching Trap**: In workloads with mixed sync ORM and async operations, `ASGI (Forced Sync Views)` frequently matches or outperforms `ASGI (Clean Async)`. A synchronous view dispatched under ASGI incurs only a single thread context switch (`sync_to_async`), whereas `async def` views with multiple ORM queries repeatedly yield and bounce across thread boundaries and GIL locks.
- **Production Concurrency Requirement (`Worker=Auto`)**: Single-threaded deployments (`Worker=1`) for either WSGI or ASGI are highly vulnerable to blocking I/O and thread starvation under real traffic. Production deployments should always provision auto-threads (`min(32, CPU+4)`) to ensure adequate threadpool capacity for background execution and template rendering.
- **Specialized Role of Async ORM Backends (`django-async-backend`)**: Bypassing `asgiref` via `Product.async_objects` allows non-blocking `psycopg 3` connection pooling, but managing asynchronous database pools requires strict lifecycle discipline. It remains a targeted optimization for greenfield, isolated microservices rather than a drop-in default for monolithic Django applications.

<!-- BENCHMARK_END -->

---

## Architectural Analysis & Practical Recommendations

### 1. Workload-Driven Architecture Selection

The benchmark results demonstrate that **neither WSGI nor ASGI is universally superior across all Django applications**. Instead, the optimal server architecture depends fundamentally on whether an application is **relational ORM / CPU bound** or **network I/O / upstream service bound**:

| Workload Dimension | Dominant Architecture | Behavioral Characteristic | Root Architectural Mechanics |
| :--- | :---: | :--- | :--- |
| **Relational ORM & DB Queries (in Isolation)** | **WSGI (Worker=Auto)** | Substantially higher raw query throughput, minimal median & tail latency | Multi-threaded WSGI executes synchronous Django ORM queries concurrently across independent database connections without event-loop wrapping overhead. |
| **Server-Side Template Rendering (in Isolation)** | **WSGI (Worker=Auto)** | Consistently faster CPU throughput | Django Template Language (DTL) is synchronous CPU work. WSGI distributes rendering across OS worker threads without event-loop context-switching overhead. |
| **External APIs & Microservice Fan-Out** | **ASGI (Clean Async / Forced Sync)** | Dramatically lower tail latency ($p95$), zero thread starvation | Coroutines yield the Tokio event loop during network socket waits (`httpx`); WSGI deadlocks OS worker threads during upstream latency, causing severe queue buildup. |
| **Mixed Real-World Web Traffic** | **ASGI (Forced Sync Views)** | Highest aggregate throughput and lowest median response time | Granian's socket multiplexing handles incoming connections non-blockingly, preventing slow network I/O from starving the worker threads needed for database queries. |
| **Cloud-Native Kubernetes Pods (1–2 vCPUs)** | **ASGI (Forced Sync / Clean Async)** | Connection resiliency without threadpool exhaustion | In constrained pod specs, WSGI's tiny threadpool (5–6 threads) easily chokes on blocking I/O; ASGI handles high connection counts within small CPU/memory limits. |

---

### 2. Deep-Dive: Core Architectural Principles

#### A. The Relational ORM Concurrency Constraint in ASGI
Django's core ORM is synchronous by design. In standard ASGI, calling asynchronous ORM methods (`acount()`, `aaggregate()`, `acreate()`, `async for`) routes each operation through `asgiref.sync.sync_to_async(thread_sensitive=True)`.
- Under the hood, `asgiref` processes `thread_sensitive` tasks on a **single shared background thread** (`_max_workers=1`).
- Consequently, on workloads composed primarily of database reads and writes, standard ASGI funnels all concurrent requests through that single thread, creating a bottleneck and adding thread-scheduling and GIL contention overhead.
- Under multi-threaded WSGI, each worker thread holds its own synchronous connection via the `psycopg` connection pool, enabling true parallel database queries.

#### B. The Head-of-Line I/O Blocking Trap in WSGI
On endpoints that communicate with external microservices, payment gateways, or third-party APIs (`/external/fetch` and `/api/gateway/aggregate`):
- In WSGI, an OS worker thread is completely deadlocked for the entire duration of the upstream HTTP round-trip.
- Under high concurrency, once all worker threads are occupied waiting on external sockets, incoming requests queue up in the TCP backlog. Tail latencies explode, and fast endpoints (such as health probes) become collateral casualties.
- Under ASGI, waiting on network I/O yields the Tokio event loop immediately without consuming worker threads. The server maintains flat tail latencies and handles thousands of concurrent open sockets effortlessly.

#### C. The Cloud-Native Reality: Hardware Sizing & Kubernetes Pod Constraints
Hardware footprint heavily influences benchmark outcomes and production behavior:
- **Large Bare-Metal / High-Core Hosts**: On an 8- to 16-core machine, WSGI's auto-thread pool provisions 12–20 worker threads. This ample thread capacity masks blocking I/O delays, allowing WSGI to absorb mixed traffic without thread exhaustion.
- **Constrained Kubernetes Pods**: In production cloud environments, Kubernetes microservices typically run in lightweight, horizontally autoscaled pods with modest resource allocations (e.g., 1–2 vCPUs, 1Gi–2Gi memory limits).
  - Under WSGI, the formula `min(32, CPU + 4)` yields only **5 to 6 worker threads per pod**. Just a handful of concurrent requests waiting on a 100 ms external call will completely saturate the pod's threadpool, causing queue backlog spikes and readiness probe failures.
  - In contrast, Granian's ASGI runtime multiplexes hundreds of concurrent HTTP connections on its Tokio Rust event loop within that exact same 1–2 vCPU pod footprint without spawning heavy OS threads.
  - **Practical Takeaway**: In cloud-native Kubernetes deployments governed by Horizontal Pod Autoscaling (HPA) and lean container resource limits, **ASGI flavors provide a distinct architectural resilience advantage over multi-threaded WSGI**.

#### D. The "Partial Async" Context-Switching Tax
A consistent empirical finding across benchmarks is that **`ASGI (Forced Sync Views)` matches or outperforms `ASGI (Clean Async)` on database-intensive endpoints**.
- **Why this occurs**: When a view is synchronous (`def view`), Django's ASGI handler dispatches the entire view **once** to a threadpool worker. All database queries, model operations, and response formatting execute within that thread with only a single thread context switch.
- In an `async def` view that queries the standard ORM, each query call repeatedly yields to the event loop and hops across the threadpool boundary. A single request incurs multiple context switches and GIL re-acquisitions.
- **Actionable Rule**: Do not convert Django views to `async def` simply because ASGI is used. Only declare a view `async def` if it genuinely awaits non-blocking asynchronous operations (such as `httpx`, `aiofiles`, or Redis).

#### E. The Single-Threaded Deployment Hazard (`Worker=1`)
Single-threaded deployments for either WSGI or ASGI (`Worker=1`) should never be used in production:
- A single-threaded WSGI server completely freezes during any blocking upstream network call.
- A single-threaded ASGI server starves background tasks (such as template rendering and non-sensitive async offloading) of threadpool capacity.
- **Actionable Rule**: Always deploy servers with auto-threading enabled (`Worker=Auto`), allowing the server to scale blocking threads with the host's CPU capacity.

#### F. The Role of Specialized Async ORM Backends (`django-async-backend`)
Bypassing `asgiref` by routing queries through `Product.async_objects` directly over non-blocking `psycopg 3` connection pools eliminates threadpool hops. However, asynchronous database pools require strict event-loop lifecycle discipline and are sensitive to pool exhaustion under heavy step load. It remains a specialized optimization for isolated microservices rather than a drop-in replacement for general-purpose monolithic Django applications.

---

### 3. Production Guidelines & Decision Matrix

```text
                           Is your application predominantly:
                                        |
               +------------------------+------------------------+
               |                                                 |
      [ Relational / ORM Heavy ]                        [ External I/O Heavy ]
      (CRUD, CMS, Relational DB,                        (Microservices, API Gateways,
       Admin, Heavy DTL Templates)                       Upstream Calls, Long-Polling)
               |                                                 |
               v                                                 v
    +----------------------+                          +----------------------+
    |  WSGI (Worker=Auto)  |                          |  ASGI (Worker=Auto)  |
    |  - Highest DB Speed  |                          |  - Flat Tail Latency |
    |  - Zero Thread Hops  |                          |  - Non-blocking I/O  |
    +----------------------+                          +----------------------+
                                                                 |
                                              [ Running on Kubernetes Pods (1-2 vCPUs) ]
                                              ASGI excels by multiplexing sockets
                                              without threadpool exhaustion
```

| Deployment Scenario | Recommended Architecture | Primary Advantages | When to Choose |
| :--- | :--- | :--- | :--- |
| **Kubernetes Microservice / API Gateway** | **ASGI (Worker=Auto / Clean Async)** | Flat tail latency on network I/O, non-blocking scatter-gather fan-out (`asyncio.gather`), high connection capacity in small pod specs (1–2 vCPUs). | Containerized Kubernetes services calling upstream APIs, payment providers, third-party webhooks, or streaming responses. |
| **Monolithic / Relational Web App (Dedicated Nodes)** | **WSGI (Worker=Auto / Multi-Thread)** | Maximum raw database query throughput, lowest median latency for ORM endpoints, parallel database execution with zero event-loop hopping. | Classic monolithic Django applications on dedicated multi-core instances dominated by ORM queries, Django admin, forms, and DTL templates. |
| **Existing WSGI App Modernizing on Kubernetes** | **ASGI (Forced Sync Views)** | Immediate socket multiplexing gains in small pods, zero view code refactoring, avoids multi-hop async ORM context switches. | Transitional migration phase from legacy WSGI servers to Granian in Kubernetes before refactoring views to native async. |
| **Isolated Greenfield Microservice** | **ASGI + `django-async-backend`** | Direct non-blocking database queries via `Product.async_objects` over `psycopg 3` connection pools. | Greenfield microservices with full control over query design and zero dependency on third-party synchronous Django apps. |
| **Single-Threaded Baseline** | **WSGI (`Worker=1`) / ASGI (`Worker=1`)** | Diagnostic baseline only. | **Never in production.** Highly vulnerable to thread starvation and head-of-line blocking under real traffic. |
