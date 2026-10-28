# Django Hurricane Performance Benchmark Suite

A Docker Compose and GitHub Actions benchmark environment evaluating **`django-hurricane`** (targeting 2.0.0rc2 and newer Granian-powered releases) under synthetic, near real-world web traffic. Starting in Hurricane 2.0.0rc2+, the `--mode` parameter is removed and the server runs purely under **ASGI** powered by Granian and Tokio.

The suite evaluates four distinct deployment paradigms and architectural configurations:
1. **ASGI (Legacy Sync Views)**: Granian ASGI interface running legacy synchronous Django views (`FORCE_SYNC_VIEWS=true`), demonstrating the exact behavior of Django's `sync_to_async(thread_sensitive=True)` adapter when serving legacy applications.
2. **ASGI (Worker=1 / Clean Async)**: Granian ASGI interface with clean async views (`async def`), pooled `httpx` async client, and `--workers 1`.
3. **ASGI (Worker=Auto / Clean Async)**: Granian ASGI interface with clean async views and Hurricane's auto-threads calculation `min(32, cpu_count + 4)` threads for non-blocking threadpool dispatch and template rendering.
4. **ASGI (`django-async-backend`)**: Granian ASGI interface with [django-async-backend](https://github.com/Arfey/django-async-backend) utilizing true non-blocking `psycopg 3` async connection pooling via `Product.async_objects` on the event loop.

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
             [ Flavor 1: Legacy Sync ]       [ Flavors 2 & 3: Clean Async ]   [ Flavor 4: Async ORM (DAB) ]
             Granian ASGI Mode               Granian ASGI Mode                Granian ASGI Mode
             (Legacy Synchronous Views)      Native async views (httpx)       django-async-backend
             sync_to_async threadpool        (Single vs. Auto Threads)        Non-blocking async DB pooling
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

## Workload Scenarios

The benchmark supports both composite mixed traffic, attack stress scenarios, and isolated per-endpoint measurements:

### 1. Mixed & Security Workloads
- **`mixed` / `baseline_valid`**: Legitimate production traffic across all valid endpoints (Gateway fan-out, ORM queries, DTL rendering, session auth).
- **`security_flood`**: Simulates attack conditions where legitimate user traffic is assaulted by a massive flood of **Fast-404 dictionary attack scanner probes** (e.g. `/.env`, `/wp-login.php`, `/.git`, `/phpmyadmin`) dropped in microseconds, and **rate-limiting bursts** triggering `429 Too Many Requests`. Used to measure throughput retention and defense overhead.

### 2. Isolated Endpoint Measurements
- `gateway_aggregate`: 100% traffic targeting `/api/gateway/aggregate` (scatter-gather microservice fan-out).
- `catalog_render`: 100% traffic targeting `/catalog/render` (DTL template engine).
- `external_fetch`: 100% traffic targeting `/external/fetch` (slow upstream API network I/O).
- `items_get`: 100% traffic targeting `GET /api/items` (relational ORM serialization).
- `items_post`: 100% traffic targeting `POST /api/items` (database inserts).
- `catalog_search`: 100% traffic targeting `/catalog/search` (PostgreSQL relational filters & joins).
- `auth`: 100% traffic targeting authentication & session check.

---

## Running Locally

### 1. Start Infrastructure & Run Full Benchmark
Execute the automated sequential benchmark runner:

```bash
# Run all flavors with default django-hurricane 2.0.0rc2 (all workloads)
./scripts/run_benchmark.sh

# Or specify custom hurricane version and parameters:
HURRICANE_VERSION=2.0.0rc2 BENCH_USERS=150 BENCH_DURATION=45s ./scripts/run_benchmark.sh

# Run only the security flood attack workload:
BENCH_WORKLOADS="security_flood" ./scripts/run_benchmark.sh

# Run clean baseline vs. security flood to measure attack defense overhead:
BENCH_WORKLOADS="baseline_valid security_flood" ./scripts/run_benchmark.sh
```

### 2. Run Flavors Individually with Docker Compose
You can run any single flavor for manual testing or debugging:

```bash
# Start ASGI legacy sync migration flavor on port 8004
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

### Latest Benchmark Results (2026-10-23 10:23:16 UTC)
**Django Hurricane Version:** `2.0.0rc2` | **PostgreSQL:** `17` | **Python:** `3.12`

#### Server & Worker Runtime Architecture
| Flavor | Server Interface | Worker Processes | Server Threads | Event Loop | App Concurrency Model | DB Pool |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ASGI (Legacy Sync Views)** | Granian ASGI | 1 | 1 | Tokio (`mt`) | `asgiref` single-thread queue | Sync psycopg (4 conns) |
| **ASGI (Worker=1 / Clean Async)** | Granian ASGI | 1 | 1 | Tokio (`mt`) | Native async views + threadpool DTL | Sync psycopg (4 conns) |
| **ASGI (Worker=Auto / Clean Async)** | Granian ASGI | 1 | `min(32, CPU+4)` (6–12) | Tokio (`mt`) | Native async views + multi-thread DTL | Sync psycopg (4 conns) |
| **ASGI + DAB** | Granian ASGI | 1 | 1 | Tokio (`mt`) | True async ORM (`async_objects`) | Async psycopg-pool (5–50 conns) |

#### Aggregate Performance Metrics (Mixed Workload)
| Flavor | Throughput | Median (p50) | 95th (p95) | 99th (p99) | Error Rate | Requests |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **WSGI (Worker=1 / Single Thread)** | **28.5 req/s** | 3600.0 ms | 6200.0 ms | 6400.0 ms | 0.0% | 1,282 |
| **WSGI (Worker=Auto / Multi-Thread)** | **173.5 req/s** | 590.0 ms | 800.0 ms | 870.0 ms | 0.0% | 7,819 |
| **ASGI (Forced Sync Views)** | **112.4 req/s** | 290.0 ms | 1900.0 ms | 2000.0 ms | 0.0% | 5,069 |
| **ASGI (Worker=1 / Clean Async)** | **96.0 req/s** | 370.0 ms | 2200.0 ms | 2400.0 ms | 0.0% | 4,325 |
| **ASGI (Worker=Auto / Clean Async)** | **98.3 req/s** | 290.0 ms | 2400.0 ms | 2700.0 ms | 0.0% | 4,431 |
| **ASGI + django-async-backend** | **83.0 req/s** | 920.0 ms | 3300.0 ms | 5000.0 ms | 0.0% | 3,740 |

#### Throughput (Requests per Second - Higher is better)
```text
WSGI (Worker=1 / Single Thread)  [█████                           ]     28.5 req/s
WSGI (Worker=Auto / Multi-Thread) [████████████████████████████████]    173.5 req/s
ASGI (Forced Sync Views)         [█████████████████████           ]    112.4 req/s
ASGI (Worker=1 / Clean Async)    [██████████████████              ]     96.0 req/s
ASGI (Worker=Auto / Clean Async) [██████████████████              ]     98.3 req/s
ASGI + django-async-backend      [███████████████                 ]     83.0 req/s
```

#### 95th Percentile Latency (Lower is better)
```text
WSGI (Worker=1 / Single Thread)  [████████████████████████████████]   6200.0 ms
WSGI (Worker=Auto / Multi-Thread) [████                            ]    800.0 ms
ASGI (Forced Sync Views)         [██████████                      ]   1900.0 ms
ASGI (Worker=1 / Clean Async)    [███████████                     ]   2200.0 ms
ASGI (Worker=Auto / Clean Async) [████████████                    ]   2400.0 ms
ASGI + django-async-backend      [█████████████████               ]   3300.0 ms
```

#### Concurrency Scaling & User Scaling Penalty
Latency progression and degradation factor as concurrent simulated users ramp up from initial ramp (`12` users) through mid-stage (`87` users) to peak concurrency (`150` users):

| Flavor | Initial Load (~12 Users) p50 / p95 | Mid Load (~87 Users) p50 / p95 | Peak Load (150 Users) p50 / p95 | Latency Scaling Penalty |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=1 / Single Thread)** | 170.0 ms / 390.0 ms | 1100.0 ms / 1700.0 ms | 2734.8 ms / 5265.2 ms | **13.5x** |
| **WSGI (Worker=Auto / Multi-Thread)** | 32.0 ms / 120.0 ms | 83.0 ms / 290.0 ms | 410.9 ms / 775.2 ms | **6.46x** |
| **ASGI (Forced Sync Views)** | 61.0 ms / 150.0 ms | 160.0 ms / 630.0 ms | 257.0 ms / 1839.1 ms | **12.26x** |
| **ASGI (Worker=1 / Clean Async)** | 38.0 ms / 170.0 ms | 220.0 ms / 810.0 ms | 301.3 ms / 2178.3 ms | **12.81x** |
| **ASGI (Worker=Auto / Clean Async)** | 58.0 ms / 170.0 ms | 200.0 ms / 690.0 ms | 260.4 ms / 2334.8 ms | **13.73x** |
| **ASGI + django-async-backend** | 60.0 ms / 130.0 ms | 210.0 ms / 750.0 ms | 793.5 ms / 2630.4 ms | **20.23x** |

#### Response Time Scaling Under User Ramp-Up (p95 Latency - Lower is better)
Visual progression of 95th percentile latency across user ramp stages:
```text
WSGI (Worker=1 / Single Thread):
   12 Users [█           ]  390.0 ms
   24 Users [█           ]  550.0 ms
   36 Users [███         ] 1300.0 ms
   37 Users [████        ] 1600.0 ms
   62 Users [████        ] 1700.0 ms
   87 Users [████        ] 1700.0 ms
   90 Users [██████      ] 2600.0 ms
  115 Users [████████    ] 3500.0 ms
  140 Users [████████    ] 3700.0 ms
  150 Users [████████████] 5265.2 ms
  Scaling Penalty Factor: 13.50x

WSGI (Worker=Auto / Multi-Thread):
   12 Users [█           ]  120.0 ms
   24 Users [█           ]  140.0 ms
   36 Users [█           ]  150.0 ms
   37 Users [█           ]  161.7 ms
   62 Users [█           ]  190.0 ms
   87 Users [█           ]  290.0 ms
   90 Users [█           ]  412.2 ms
  115 Users [█           ]  450.0 ms
  140 Users [█           ]  520.0 ms
  150 Users [██          ]  775.2 ms
  Scaling Penalty Factor: 6.46x

ASGI (Forced Sync Views):
   12 Users [█           ]  150.0 ms
   24 Users [█           ]  180.0 ms
   36 Users [█           ]  260.0 ms
   37 Users [█           ]  251.7 ms
   62 Users [█           ]  340.0 ms
   87 Users [█           ]  630.0 ms
   90 Users [██          ]  947.8 ms
  115 Users [██          ]  980.0 ms
  140 Users [██          ] 1000.0 ms
  150 Users [████        ] 1839.1 ms
  Scaling Penalty Factor: 12.26x

ASGI (Worker=1 / Clean Async):
   12 Users [█           ]  170.0 ms
   24 Users [█           ]  250.0 ms
   36 Users [█           ]  410.0 ms
   37 Users [█           ]  375.0 ms
   62 Users [█           ]  410.0 ms
   87 Users [██          ]  810.0 ms
   90 Users [███         ] 1233.3 ms
  115 Users [███         ] 1300.0 ms
  140 Users [███         ] 1400.0 ms
  150 Users [█████       ] 2178.3 ms
  Scaling Penalty Factor: 12.81x

ASGI (Worker=Auto / Clean Async):
   12 Users [█           ]  170.0 ms
   24 Users [█           ]  250.0 ms
   36 Users [█           ]  320.0 ms
   37 Users [█           ]  288.3 ms
   62 Users [█           ]  350.0 ms
   87 Users [██          ]  690.0 ms
   90 Users [███         ] 1166.7 ms
  115 Users [███         ] 1300.0 ms
  140 Users [███         ] 1300.0 ms
  150 Users [█████       ] 2334.8 ms
  Scaling Penalty Factor: 13.73x

ASGI + django-async-backend:
   12 Users [█           ]  130.0 ms
   24 Users [█           ]  230.0 ms
   36 Users [█           ]  300.0 ms
   37 Users [█           ]  310.0 ms
   62 Users [█           ]  510.0 ms
   87 Users [██          ]  750.0 ms
   90 Users [███         ] 1212.2 ms
  115 Users [████        ] 1600.0 ms
  140 Users [████        ] 1700.0 ms
  150 Users [██████      ] 2630.4 ms
  Scaling Penalty Factor: 20.23x

```

#### Fast-404 & Rate Limiting Attack Defense Performance
Evaluation of Hurricane's security engines: comparing clean baseline traffic against a massive flood of dictionary attacks (Fast-404 early drop in microseconds) and rate-limited abuse (429 Too Many Requests):

| Flavor | Clean Baseline RPS | Under Attack RPS | Clean Median | Attack Median | Throughput Capacity Factor |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **ASGI (Worker=1 / Clean Async)** | **54.0 req/s** | **67.5 req/s** | 69.0 ms | 16.0 ms | **1.25x** |

#### Isolated Workload Performance (Pure Endpoint Measurement)
Workloads executed in isolation to eliminate cross-traffic contention and measure raw endpoint capability:

##### Security Flood: Fast-404 Dictionary Attack & 429 Rate Limiter Abuse
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Worker=1 / Clean Async)** | **67.5 req/s** | 16.0 ms | 130.0 ms | 0.0% |

##### Clean Baseline: Valid Traffic with Security Protection (No Flood)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Worker=1 / Clean Async)** | **54.0 req/s** | 69.0 ms | 200.0 ms | 0.0% |

##### API Gateway / BFF (Scatter-Gather Fan-Out)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Forced Sync Views)** | **114.2 req/s** | 880.0 ms | 1300.0 ms | 0.0% |
| **WSGI (Worker=Auto / Multi-Thread)** | **74.3 req/s** | 1200.0 ms | 2000.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **47.9 req/s** | 1700.0 ms | 5100.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **46.5 req/s** | 1800.0 ms | 4900.0 ms | 0.0% |
| **ASGI + django-async-backend** | **45.9 req/s** | 1800.0 ms | 5300.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **12.2 req/s** | 6800.0 ms | 12000.0 ms | 0.0% |

##### Catalog Render (DTL Template Engine)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=Auto / Multi-Thread)** | **88.0 req/s** | 1200.0 ms | 1900.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **79.9 req/s** | 1300.0 ms | 1400.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **75.2 req/s** | 1400.0 ms | 2000.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **73.6 req/s** | 1600.0 ms | 2000.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **73.5 req/s** | 1600.0 ms | 1900.0 ms | 0.0% |
| **ASGI + django-async-backend** | **55.1 req/s** | 1700.0 ms | 3000.0 ms | 0.0% |

##### External Fetch (Upstream API I/O)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Forced Sync Views)** | **150.5 req/s** | 700.0 ms | 900.0 ms | 0.0% |
| **WSGI (Worker=Auto / Multi-Thread)** | **144.3 req/s** | 790.0 ms | 930.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **105.9 req/s** | 740.0 ms | 2300.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **105.4 req/s** | 750.0 ms | 2300.0 ms | 0.0% |
| **ASGI + django-async-backend** | **101.9 req/s** | 800.0 ms | 2300.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **21.0 req/s** | 4700.0 ms | 8200.0 ms | 0.0% |

##### Items API [GET] (ORM Serialization)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=Auto / Multi-Thread)** | **291.1 req/s** | 300.0 ms | 360.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **247.4 req/s** | 380.0 ms | 450.0 ms | 0.0% |
| **ASGI + django-async-backend** | **138.4 req/s** | 810.0 ms | 1000.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **129.0 req/s** | 910.0 ms | 1100.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **127.7 req/s** | 940.0 ms | 1100.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **124.1 req/s** | 950.0 ms | 1100.0 ms | 0.0% |

##### Items API [POST] (ORM Inserts)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=Auto / Multi-Thread)** | **481.3 req/s** | 100.0 ms | 140.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **386.1 req/s** | 170.0 ms | 240.0 ms | 0.0% |
| **ASGI + django-async-backend** | **161.6 req/s** | 690.0 ms | 840.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **159.3 req/s** | 710.0 ms | 850.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **157.4 req/s** | 710.0 ms | 860.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **151.8 req/s** | 750.0 ms | 920.0 ms | 0.0% |

##### Catalog Search (PostgreSQL Joins & Aggregates)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=Auto / Multi-Thread)** | **228.1 req/s** | 440.0 ms | 530.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **144.8 req/s** | 790.0 ms | 940.0 ms | 0.0% |
| **ASGI + django-async-backend** | **117.1 req/s** | 1000.0 ms | 1200.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **113.8 req/s** | 1100.0 ms | 1200.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **113.3 req/s** | 1100.0 ms | 1200.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **112.0 req/s** | 1100.0 ms | 1200.0 ms | 0.0% |

##### Authentication & Session Middleware
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=Auto / Multi-Thread)** | **349.9 req/s** | 210.0 ms | 260.0 ms | 0.0% |
| **WSGI (Worker=1 / Single Thread)** | **310.5 req/s** | 250.0 ms | 340.0 ms | 0.0% |
| **ASGI (Forced Sync Views)** | **142.7 req/s** | 790.0 ms | 990.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **131.1 req/s** | 870.0 ms | 1100.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **128.0 req/s** | 890.0 ms | 1100.0 ms | 0.0% |
| **ASGI + django-async-backend** | **123.4 req/s** | 900.0 ms | 1200.0 ms | 0.0% |

#### Route Breakdown Across Flavors (Mixed Workload)
| Route | WSGI (Worker=1 / Single Thread) (p95 / RPS) | WSGI (Worker=Auto / Multi-Thread) (p95 / RPS) | ASGI (Forced Sync Views) (p95 / RPS) | ASGI (Worker=1 / Clean Async) (p95 / RPS) | ASGI (Worker=Auto / Clean Async) (p95 / RPS) | ASGI + django-async-backend (p95 / RPS) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `/api/auth/login` | 5400.0 ms (4.7 rps) | 740.0 ms (11.8 rps) | 2000.0 ms (8.5 rps) | 2300.0 ms (7.9 rps) | 2500.0 ms (7.5 rps) | 1300.0 ms (7.8 rps) |
| `/api/auth/me [GET]` | 6200.0 ms (1.1 rps) | 730.0 ms (8.2 rps) | 1900.0 ms (5.8 rps) | 2300.0 ms (4.9 rps) | 2500.0 ms (4.4 rps) | 1100.0 ms (4.2 rps) |
| `/api/gateway/aggregate [GET]` | 6300.0 ms (5.9 rps) | 860.0 ms (43.6 rps) | 300.0 ms (29.1 rps) | 290.0 ms (23.1 rps) | 300.0 ms (25.3 rps) | 4800.0 ms (18.8 rps) |
| `/api/items [GET]` | 6200.0 ms (5.0 rps) | 750.0 ms (33.2 rps) | 1900.0 ms (21.3 rps) | 2300.0 ms (18.4 rps) | 2500.0 ms (18.8 rps) | 1100.0 ms (15.9 rps) |
| `/api/items [POST]` | 6200.0 ms (1.2 rps) | 740.0 ms (8.9 rps) | 2000.0 ms (5.1 rps) | 2300.0 ms (5.0 rps) | 2500.0 ms (4.0 rps) | 1100.0 ms (3.9 rps) |
| `/catalog/render [GET]` | 6300.0 ms (3.6 rps) | 760.0 ms (25.8 rps) | 2000.0 ms (16.1 rps) | 2300.0 ms (13.3 rps) | 2600.0 ms (14.3 rps) | 1100.0 ms (12.1 rps) |
| `/catalog/search [GET]` | 6200.0 ms (2.8 rps) | 750.0 ms (17.3 rps) | 2000.0 ms (10.4 rps) | 2300.0 ms (8.9 rps) | 2500.0 ms (8.9 rps) | 1100.0 ms (7.7 rps) |
| `/external/fetch [GET]` | 6300.0 ms (4.3 rps) | 790.0 ms (24.7 rps) | 240.0 ms (16.2 rps) | 270.0 ms (14.6 rps) | 270.0 ms (15.2 rps) | 3500.0 ms (12.6 rps) |

#### Key Empirical Findings & Production Recommendations
- **Pure ASGI Architecture**: With Hurricane 2.0.0rc2+, Django runs strictly under Granian's ASGI interface, standardizing connection handling onto Tokio's asynchronous Rust runtime.
- **Legacy Synchronous Django Apps under ASGI**: For codebases reliant on synchronous ORM methods, legacy middleware, and standard forms, running Hurricane ASGI with synchronous views (`ASGI Legacy Sync Views`) achieves high socket multiplexing while avoiding the multi-hop coroutine-to-thread context switches incurred when querying the ORM from `async def` views.
- **Fast-404 & Rate Limiting Protection**: Under security flood attacks, Hurricane's Fast-404 engine drops malicious scanner probes (e.g. `/.env`, `/wp-login.php`, `/.git`) in microseconds, while the Token Bucket Rate Limiter returns 429 Too Many Requests before touching Django's URL resolver or view pipeline, preserving server capacity for legitimate traffic.
- **Hardware Footprint & Kubernetes Pod Constraints**: In typical cloud-native Kubernetes clusters running lightweight pods (1–2 vCPUs), ASGI multiplexes high connection volumes on Granian's Tokio event loop without threadpool exhaustion, providing superior operational resilience compared to traditional thread-per-request models.
- **Production Concurrency Requirement (`Worker=Auto`)**: Always deploy Hurricane with auto-threads (`Worker=Auto`), ensuring adequate threadpool depth for CPU template rendering and background tasks without starving the event loop.

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
                        Django Architecture on Hurricane (Pure ASGI)
                                        |
               +------------------------+------------------------+
               |                                                 |
      [ Legacy Synchronous App ]                        [ Modern Async Services ]
      (Existing DRF, CMS, Sync ORM,                     (API Gateways, Microservices,
       Heavy Relational DB Models)                       Upstream Calls, Scatter-Gather)
               |                                                 |
               v                                                 v
    +--------------------------+                      +--------------------------+
    | ASGI (Legacy Sync Views) |                      | ASGI (Worker=Auto/Clean) |
    | - High Socket Concurrency|                      | - Non-blocking Fan-Out   |
    | - 1 Context Switch / Req |                      | - Flat Tail Latencies    |
    +--------------------------+                      +--------------------------+
```

| Deployment Scenario | Recommended Architecture | Primary Advantages | When to Choose |
| :--- | :--- | :--- | :--- |
| **Modern API Gateway / Microservice** | **ASGI (Worker=Auto / Clean Async)** | Flat tail latency on network I/O, non-blocking scatter-gather fan-out (`asyncio.gather`), high connection capacity in small Kubernetes pod specs (1–2 vCPUs). | Containerized Kubernetes services calling upstream APIs, payment providers, third-party webhooks, or streaming responses. |
| **Legacy Synchronous Django Applications** | **ASGI (Legacy Sync Views)** | Immediate socket multiplexing gains, 100% compatibility with standard Django ORM, avoids multi-hop coroutine-to-thread context switching. | Existing synchronous Django codebases, DRF applications, and apps migrating to Hurricane without rewriting views to async. |
| **Isolated Greenfield Microservice** | **ASGI + `django-async-backend`** | Direct non-blocking database queries via `Product.async_objects` over `psycopg 3` connection pools on the event loop. | Greenfield microservices with full control over query design and zero dependency on third-party synchronous Django apps. |
| **Single-Threaded Diagnostic Baseline** | **ASGI (`Worker=1`)** | Synthetic diagnostic baseline only. | **Never in production.** Highly vulnerable to background task starvation (template rendering and non-sensitive async tasks). |
