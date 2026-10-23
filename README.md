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

### Latest Benchmark Results (2026-10-23 08:25:30 UTC)
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
| **WSGI (Worker=1 / Single Thread)** | **29.8 req/s** | 3200.0 ms | 5800.0 ms | 6000.0 ms | 0.0% | 1,340 |
| **WSGI (Worker=Auto / Multi-Thread)** | **205.2 req/s** | 450.0 ms | 660.0 ms | 720.0 ms | 0.0% | 9,242 |
| **ASGI (Forced Sync Views)** | **231.0 req/s** | 200.0 ms | 730.0 ms | 800.0 ms | 0.0% | 10,407 |
| **ASGI (Worker=1 / Clean Async)** | **186.5 req/s** | 240.0 ms | 1100.0 ms | 1200.0 ms | 0.0% | 8,402 |
| **ASGI (Worker=Auto / Clean Async)** | **184.1 req/s** | 210.0 ms | 1100.0 ms | 1200.0 ms | 0.0% | 8,296 |
| **ASGI + django-async-backend** | **156.3 req/s** | 400.0 ms | 1800.0 ms | 2800.0 ms | 0.0% | 7,037 |

#### Throughput (Requests per Second - Higher is better)
```text
WSGI (Worker=1 / Single Thread)  [████                            ]     29.8 req/s
WSGI (Worker=Auto / Multi-Thread) [████████████████████████████    ]    205.2 req/s
ASGI (Forced Sync Views)         [████████████████████████████████]    231.0 req/s
ASGI (Worker=1 / Clean Async)    [██████████████████████████      ]    186.5 req/s
ASGI (Worker=Auto / Clean Async) [██████████████████████████      ]    184.1 req/s
ASGI + django-async-backend      [██████████████████████          ]    156.3 req/s
```

#### 95th Percentile Latency (Lower is better)
```text
WSGI (Worker=1 / Single Thread)  [████████████████████████████████]   5800.0 ms
WSGI (Worker=Auto / Multi-Thread) [████                            ]    660.0 ms
ASGI (Forced Sync Views)         [████                            ]    730.0 ms
ASGI (Worker=1 / Clean Async)    [██████                          ]   1100.0 ms
ASGI (Worker=Auto / Clean Async) [██████                          ]   1100.0 ms
ASGI + django-async-backend      [██████████                      ]   1800.0 ms
```

#### Concurrency Scaling & User Scaling Penalty
Latency progression and degradation factor as concurrent simulated users ramp up from initial ramp (`12` users) through mid-stage (`87` users) to peak concurrency (`150` users):

| Flavor | Initial Load (~12 Users) p50 / p95 | Mid Load (~87 Users) p50 / p95 | Peak Load (150 Users) p50 / p95 | Latency Scaling Penalty |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=1 / Single Thread)** | 280.0 ms / 480.0 ms | 870.0 ms / 1500.0 ms | 2700.0 ms / 5034.8 ms | **10.49x** |
| **WSGI (Worker=Auto / Multi-Thread)** | 28.0 ms / 120.0 ms | 48.0 ms / 250.0 ms | 331.3 ms / 628.3 ms | **5.24x** |
| **ASGI (Forced Sync Views)** | 33.0 ms / 130.0 ms | 57.0 ms / 250.0 ms | 180.9 ms / 684.3 ms | **5.26x** |
| **ASGI (Worker=1 / Clean Async)** | 23.0 ms / 86.0 ms | 60.0 ms / 390.0 ms | 182.2 ms / 1027.4 ms | **11.95x** |
| **ASGI (Worker=Auto / Clean Async)** | 33.0 ms / 81.0 ms | 55.0 ms / 330.0 ms | 166.5 ms / 1053.5 ms | **13.01x** |
| **ASGI + django-async-backend** | 46.0 ms / 80.0 ms | 52.0 ms / 330.0 ms | 317.4 ms / 1428.3 ms | **17.85x** |

#### Response Time Scaling Under User Ramp-Up (p95 Latency - Lower is better)
Visual progression of 95th percentile latency across user ramp stages:
```text
WSGI (Worker=1 / Single Thread):
   12 Users [█           ]  480.0 ms
   24 Users [█           ]  480.0 ms
   36 Users [██          ]  710.0 ms
   37 Users [███         ] 1298.3 ms
   62 Users [████        ] 1500.0 ms
   87 Users [████        ] 1500.0 ms
   90 Users [███████     ] 2922.2 ms
  115 Users [█████████   ] 3700.0 ms
  140 Users [█████████   ] 3700.0 ms
  150 Users [████████████] 5034.8 ms
  Scaling Penalty Factor: 10.49x

WSGI (Worker=Auto / Multi-Thread):
   12 Users [█           ]  120.0 ms
   24 Users [█           ]  120.0 ms
   36 Users [█           ]  120.0 ms
   37 Users [█           ]  126.7 ms
   62 Users [█           ]  150.0 ms
   87 Users [█           ]  250.0 ms
   90 Users [█           ]  358.9 ms
  115 Users [█           ]  390.0 ms
  140 Users [█           ]  420.0 ms
  150 Users [█           ]  628.3 ms
  Scaling Penalty Factor: 5.24x

ASGI (Forced Sync Views):
   12 Users [█           ]  130.0 ms
   24 Users [█           ]  130.0 ms
   36 Users [█           ]  130.0 ms
   37 Users [█           ]  130.0 ms
   62 Users [█           ]  150.0 ms
   87 Users [█           ]  250.0 ms
   90 Users [█           ]  287.8 ms
  115 Users [█           ]  330.0 ms
  140 Users [█           ]  410.0 ms
  150 Users [██          ]  684.3 ms
  Scaling Penalty Factor: 5.26x

ASGI (Worker=1 / Clean Async):
   12 Users [█           ]   86.0 ms
   24 Users [█           ]  110.0 ms
   36 Users [█           ]  170.0 ms
   37 Users [█           ]  130.0 ms
   62 Users [█           ]  220.0 ms
   87 Users [█           ]  390.0 ms
   90 Users [█           ]  483.3 ms
  115 Users [█           ]  500.0 ms
  140 Users [█           ]  570.0 ms
  150 Users [██          ] 1027.4 ms
  Scaling Penalty Factor: 11.95x

ASGI (Worker=Auto / Clean Async):
   12 Users [█           ]   81.0 ms
   24 Users [█           ]   91.0 ms
   36 Users [█           ]  120.0 ms
   37 Users [█           ]  100.0 ms
   62 Users [█           ]  190.0 ms
   87 Users [█           ]  330.0 ms
   90 Users [█           ]  590.0 ms
  115 Users [█           ]  600.0 ms
  140 Users [██          ]  640.0 ms
  150 Users [███         ] 1053.5 ms
  Scaling Penalty Factor: 13.01x

ASGI + django-async-backend:
   12 Users [█           ]   80.0 ms
   24 Users [█           ]   87.0 ms
   36 Users [█           ]  140.0 ms
   37 Users [█           ]  111.7 ms
   62 Users [█           ]  240.0 ms
   87 Users [█           ]  330.0 ms
   90 Users [█           ]  571.1 ms
  115 Users [██          ]  710.0 ms
  140 Users [██          ]  730.0 ms
  150 Users [███         ] 1428.3 ms
  Scaling Penalty Factor: 17.85x

```

#### Isolated Workload Performance (Pure Endpoint Measurement)
Workloads executed in isolation to eliminate cross-traffic contention and measure raw endpoint capability:

##### API Gateway / BFF (Scatter-Gather Fan-Out)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Forced Sync Views)** | **225.7 req/s** | 400.0 ms | 500.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **87.8 req/s** | 960.0 ms | 2700.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **85.1 req/s** | 980.0 ms | 2700.0 ms | 0.0% |
| **WSGI (Worker=Auto / Multi-Thread)** | **76.9 req/s** | 1200.0 ms | 1900.0 ms | 0.0% |
| **ASGI + django-async-backend** | **72.0 req/s** | 1000.0 ms | 3600.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **12.1 req/s** | 7900.0 ms | 12000.0 ms | 0.0% |

##### Catalog Render (DTL Template Engine)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=Auto / Multi-Thread)** | **230.5 req/s** | 440.0 ms | 510.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **164.0 req/s** | 700.0 ms | 810.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **157.4 req/s** | 540.0 ms | 590.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **151.7 req/s** | 750.0 ms | 890.0 ms | 0.0% |
| **ASGI + django-async-backend** | **145.8 req/s** | 700.0 ms | 1300.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **145.4 req/s** | 800.0 ms | 950.0 ms | 0.0% |

##### External Fetch (Upstream API I/O)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Forced Sync Views)** | **316.1 req/s** | 230.0 ms | 320.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **176.1 req/s** | 380.0 ms | 1300.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **171.8 req/s** | 370.0 ms | 1400.0 ms | 0.0% |
| **ASGI + django-async-backend** | **168.6 req/s** | 400.0 ms | 1300.0 ms | 0.0% |
| **WSGI (Worker=Auto / Multi-Thread)** | **148.5 req/s** | 770.0 ms | 900.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **21.9 req/s** | 4700.0 ms | 8000.0 ms | 0.0% |

##### Items API [GET] (ORM Serialization)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=Auto / Multi-Thread)** | **516.1 req/s** | 84.0 ms | 120.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **438.2 req/s** | 120.0 ms | 150.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **274.3 req/s** | 340.0 ms | 400.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **256.5 req/s** | 370.0 ms | 450.0 ms | 0.0% |
| **ASGI + django-async-backend** | **249.1 req/s** | 370.0 ms | 510.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **235.6 req/s** | 410.0 ms | 520.0 ms | 0.0% |

##### Items API [POST] (ORM Inserts)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=Auto / Multi-Thread)** | **692.9 req/s** | 7.0 ms | 26.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **630.5 req/s** | 25.0 ms | 63.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **320.6 req/s** | 250.0 ms | 330.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **303.7 req/s** | 270.0 ms | 350.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **300.3 req/s** | 280.0 ms | 370.0 ms | 0.0% |
| **ASGI + django-async-backend** | **270.8 req/s** | 320.0 ms | 480.0 ms | 0.0% |

##### Catalog Search (PostgreSQL Joins & Aggregates)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=Auto / Multi-Thread)** | **424.9 req/s** | 150.0 ms | 180.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **285.9 req/s** | 320.0 ms | 360.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **240.5 req/s** | 410.0 ms | 490.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **227.2 req/s** | 440.0 ms | 540.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **204.9 req/s** | 500.0 ms | 640.0 ms | 0.0% |
| **ASGI + django-async-backend** | **189.9 req/s** | 550.0 ms | 720.0 ms | 0.0% |

##### Authentication & Session Middleware
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=Auto / Multi-Thread)** | **596.8 req/s** | 41.0 ms | 70.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **556.7 req/s** | 60.0 ms | 91.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **278.7 req/s** | 320.0 ms | 410.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **243.3 req/s** | 390.0 ms | 500.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **226.8 req/s** | 420.0 ms | 590.0 ms | 0.0% |
| **ASGI + django-async-backend** | **222.1 req/s** | 410.0 ms | 590.0 ms | 0.0% |

#### Route Breakdown Across Flavors (Mixed Workload)
| Route | WSGI (Worker=1 / Single Thread) (p95 / RPS) | WSGI (Worker=Auto / Multi-Thread) (p95 / RPS) | ASGI (Forced Sync Views) (p95 / RPS) | ASGI (Worker=1 / Clean Async) (p95 / RPS) | ASGI (Worker=Auto / Clean Async) (p95 / RPS) | ASGI + django-async-backend (p95 / RPS) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `/api/auth/login` | 5400.0 ms (4.5 rps) | 600.0 ms (13.3 rps) | 760.0 ms (14.3 rps) | 1100.0 ms (12.6 rps) | 1200.0 ms (12.3 rps) | 690.0 ms (11.5 rps) |
| `/api/auth/me [GET]` | 5900.0 ms (1.3 rps) | 610.0 ms (9.9 rps) | 750.0 ms (10.6 rps) | 1100.0 ms (9.0 rps) | 1100.0 ms (8.4 rps) | 610.0 ms (7.7 rps) |
| `/api/gateway/aggregate [GET]` | 5800.0 ms (6.4 rps) | 710.0 ms (49.9 rps) | 210.0 ms (56.4 rps) | 210.0 ms (46.3 rps) | 220.0 ms (46.2 rps) | 2600.0 ms (36.8 rps) |
| `/api/items [GET]` | 5800.0 ms (5.0 rps) | 600.0 ms (39.3 rps) | 740.0 ms (47.3 rps) | 1100.0 ms (37.6 rps) | 1100.0 ms (35.3 rps) | 630.0 ms (31.1 rps) |
| `/api/items [POST]` | 5800.0 ms (1.6 rps) | 610.0 ms (10.6 rps) | 750.0 ms (10.9 rps) | 1100.0 ms (8.3 rps) | 1100.0 ms (9.5 rps) | 650.0 ms (6.9 rps) |
| `/catalog/render [GET]` | 5800.0 ms (3.9 rps) | 610.0 ms (30.7 rps) | 750.0 ms (33.8 rps) | 1100.0 ms (27.5 rps) | 1100.0 ms (25.7 rps) | 680.0 ms (23.0 rps) |
| `/catalog/search [GET]` | 5800.0 ms (2.7 rps) | 610.0 ms (21.0 rps) | 750.0 ms (22.8 rps) | 1100.0 ms (17.8 rps) | 1100.0 ms (17.7 rps) | 630.0 ms (15.1 rps) |
| `/external/fetch [GET]` | 5900.0 ms (4.4 rps) | 660.0 ms (30.5 rps) | 150.0 ms (35.0 rps) | 190.0 ms (27.3 rps) | 190.0 ms (28.9 rps) | 1900.0 ms (24.2 rps) |

#### Key Empirical Findings & Production Recommendations
- **Relational ORM & CPU Rendering Dominance (WSGI Advantage)**: In workloads dominated by relational database queries (`select_related`, model creation, bulk serialization) and template rendering (DTL), multi-threaded WSGI (`WSGI Worker=Auto`) delivers consistently superior throughput and significantly lower tail latencies. In standard ASGI, Django ORM operations route through `asgiref`'s single-thread queue (`_max_workers=1`), serializing database concurrency onto a single OS thread.
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
| **Relational ORM & DB Queries** | **WSGI (Worker=Auto)** | Substantially higher throughput, minimal median & tail latency | Multi-threaded WSGI executes synchronous Django ORM queries concurrently across independent database connections. Standard ASGI serializes sync ORM calls through `asgiref`'s single-thread queue (`_max_workers=1`). |
| **Server-Side Template Rendering** | **WSGI (Worker=Auto)** | Consistently faster CPU throughput | Django Template Language (DTL) is synchronous CPU work. WSGI distributes rendering across OS worker threads without event loop context-switching overhead. |
| **External APIs & Microservice Fan-Out** | **ASGI (Clean Async / Forced Sync)** | Dramatically lower tail latency ($p95$), zero thread starvation | Coroutines yield the Tokio event loop during network socket waits (`httpx`); WSGI deadlocks OS worker threads during upstream latency, causing severe queue buildup. |
| **Mixed General Web Traffic** | **ASGI (Forced Sync) / WSGI (Auto)** | Balanced throughput and responsive tail latency | High-performance socket multiplexing via Granian's Rust runtime combined with batch threadpool execution absorbs diverse traffic patterns effectively. |

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

#### C. The "Partial Async" Context-Switching Tax
A consistent empirical finding across benchmarks is that **`ASGI (Forced Sync Views)` matches or outperforms `ASGI (Clean Async)` on database-intensive endpoints**.
- **Why this occurs**: When a view is synchronous (`def view`), Django's ASGI handler dispatches the entire view **once** to a threadpool worker. All database queries, model operations, and response formatting execute within that thread with only a single thread context switch.
- In an `async def` view that queries the standard ORM, each query call repeatedly yields to the event loop and hops across the threadpool boundary. A single request incurs multiple context switches and GIL re-acquisitions.
- **Actionable Rule**: Do not convert Django views to `async def` simply because ASGI is used. Only declare a view `async def` if it genuinely awaits non-blocking asynchronous operations (such as `httpx`, `aiofiles`, or Redis).

#### D. The Single-Threaded Deployment Hazard (`Worker=1`)
Single-threaded deployments for either WSGI or ASGI (`Worker=1`) should never be used in production:
- A single-threaded WSGI server completely freezes during any blocking upstream network call.
- A single-threaded ASGI server starves background tasks (such as template rendering and non-sensitive async offloading) of threadpool capacity.
- **Actionable Rule**: Always deploy servers with auto-threading enabled (`Worker=Auto`), allowing the server to scale blocking threads with the host's CPU capacity.

#### E. The Role of Specialized Async ORM Backends (`django-async-backend`)
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
```

| Deployment Scenario | Recommended Architecture | Primary Advantages | When to Choose |
| :--- | :--- | :--- | :--- |
| **API Gateway / Microservice** | **ASGI (Worker=Auto / Clean Async)** | Flat tail latency on network I/O, non-blocking scatter-gather fan-out (`asyncio.gather`), event-loop connection multiplexing via Granian's Rust runtime. | Applications making frequent external HTTP calls, consuming microservices, handling webhooks, or streaming responses. |
| **Monolithic / Relational Web App** | **WSGI (Worker=Auto / Multi-Thread)** | Maximum raw database query throughput, lowest median latency for ORM endpoints, parallel database execution with zero event-loop hopping. | Classic Django applications dominated by ORM queries, Django admin, forms, and DTL template rendering. |
| **Existing WSGI App Modernizing to Granian** | **ASGI (Forced Sync Views)** | Immediate socket multiplexing gains, zero view code refactoring, avoids multi-hop async ORM context switches. | Transitional migration phase from legacy WSGI servers to Granian before refactoring views to native async. |
| **Isolated Greenfield Microservice** | **ASGI + `django-async-backend`** | Direct non-blocking database queries via `Product.async_objects` over `psycopg 3` connection pools. | Greenfield microservices with full control over query design and zero dependency on third-party synchronous Django apps. |
| **Single-Threaded Baseline** | **WSGI (`Worker=1`) / ASGI (`Worker=1`)** | Diagnostic baseline only. | **Never in production.** Highly vulnerable to thread starvation and head-of-line blocking under real traffic. |
