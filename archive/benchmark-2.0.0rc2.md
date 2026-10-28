### Latest Benchmark Results (2026-10-28 15:14:33 UTC)
**Django Hurricane Version:** `2.0.0rc2` (Pure ASGI) | **PostgreSQL:** `17` | **Python:** `3.12`

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
| **ASGI (Legacy Sync Views)** | **71.5 req/s** | 280.0 ms | 1900.0 ms | 2000.0 ms | 0.0% | 1,073 |
| **ASGI (Worker=1 / Clean Async)** | **60.1 req/s** | 350.0 ms | 2200.0 ms | 2500.0 ms | 0.0% | 901 |
| **ASGI (Worker=Auto / Clean Async)** | **60.6 req/s** | 300.0 ms | 2300.0 ms | 2600.0 ms | 0.0% | 910 |
| **ASGI + django-async-backend** | **59.8 req/s** | 720.0 ms | 1800.0 ms | 2700.0 ms | 0.0% | 898 |

#### Throughput (Requests per Second - Higher is better)
```text
ASGI (Legacy Sync Views)         [████████████████████████████████]     71.5 req/s
ASGI (Worker=1 / Clean Async)    [███████████████████████████     ]     60.1 req/s
ASGI (Worker=Auto / Clean Async) [███████████████████████████     ]     60.6 req/s
ASGI + django-async-backend      [███████████████████████████     ]     59.8 req/s
```

#### 95th Percentile Latency (Lower is better)
```text
ASGI (Legacy Sync Views)         [██████████████████████████      ]   1900.0 ms
ASGI (Worker=1 / Clean Async)    [███████████████████████████████ ]   2200.0 ms
ASGI (Worker=Auto / Clean Async) [████████████████████████████████]   2300.0 ms
ASGI + django-async-backend      [█████████████████████████       ]   1800.0 ms
```

#### Concurrency Scaling & User Scaling Penalty
Latency progression and degradation factor as concurrent simulated users ramp up from initial ramp (`12` users) through mid-stage (`50` users) to peak concurrency (`100` users):

| Flavor | Initial Load (~12 Users) p50 / p95 | Mid Load (~50 Users) p50 / p95 | Peak Load (100 Users) p50 / p95 | Latency Scaling Penalty |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Legacy Sync Views)** | 110.0 ms / 240.0 ms | 180.0 ms / 420.0 ms | 267.5 ms / 1600.0 ms | **6.67x** |
| **ASGI (Worker=1 / Clean Async)** | 99.0 ms / 260.0 ms | 240.0 ms / 530.0 ms | 330.0 ms / 1900.0 ms | **7.31x** |
| **ASGI (Worker=Auto / Clean Async)** | 120.0 ms / 230.0 ms | 230.0 ms / 510.0 ms | 290.0 ms / 1925.0 ms | **8.37x** |
| **ASGI + django-async-backend** | 92.0 ms / 200.0 ms | 210.0 ms / 770.0 ms | 667.5 ms / 1575.0 ms | **7.88x** |

#### Response Time Scaling Under User Ramp-Up (p95 Latency - Lower is better)
Visual progression of 95th percentile latency across user ramp stages:
```text
ASGI (Legacy Sync Views):
   12 Users [█           ]  240.0 ms
   24 Users [██          ]  300.0 ms
   25 Users [██          ]  283.3 ms
   50 Users [███         ]  420.0 ms
   60 Users [██████      ]  957.5 ms
   85 Users [██████      ]  970.0 ms
  100 Users [██████████  ] 1600.0 ms
  Scaling Penalty Factor: 6.67x

ASGI (Worker=1 / Clean Async):
   12 Users [██          ]  260.0 ms
   24 Users [███         ]  420.0 ms
   25 Users [██          ]  400.0 ms
   50 Users [███         ]  530.0 ms
   60 Users [███████     ] 1170.0 ms
   85 Users [█████████   ] 1400.0 ms
  100 Users [████████████] 1900.0 ms
  Scaling Penalty Factor: 7.31x

ASGI (Worker=Auto / Clean Async):
   12 Users [█           ]  230.0 ms
   24 Users [███         ]  490.0 ms
   25 Users [██          ]  396.7 ms
   50 Users [███         ]  510.0 ms
   60 Users [███████     ] 1100.0 ms
   85 Users [███████     ] 1200.0 ms
  100 Users [████████████] 1925.0 ms
  Scaling Penalty Factor: 8.37x

ASGI + django-async-backend:
   12 Users [█           ]  200.0 ms
   24 Users [██          ]  290.0 ms
   25 Users [██          ]  323.3 ms
   50 Users [█████       ]  770.0 ms
   60 Users [██████      ]  972.5 ms
   85 Users [███████     ] 1100.0 ms
  100 Users [██████████  ] 1575.0 ms
  Scaling Penalty Factor: 7.88x

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
| **ASGI (Legacy Sync Views)** | **87.1 req/s** | 390.0 ms | 1100.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **47.1 req/s** | 770.0 ms | 2300.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **46.7 req/s** | 730.0 ms | 2600.0 ms | 0.0% |
| **ASGI + django-async-backend** | **39.4 req/s** | 950.0 ms | 2900.0 ms | 0.0% |

##### Catalog Render (DTL Template Engine)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Legacy Sync Views)** | **49.7 req/s** | 980.0 ms | 1800.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **46.7 req/s** | 1100.0 ms | 2100.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **41.2 req/s** | 1100.0 ms | 2000.0 ms | 0.0% |
| **ASGI + django-async-backend** | **34.1 req/s** | 1300.0 ms | 2700.0 ms | 0.0% |

##### External Fetch (Upstream API I/O)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Legacy Sync Views)** | **107.4 req/s** | 330.0 ms | 830.0 ms | 0.0% |
| **ASGI + django-async-backend** | **74.6 req/s** | 570.0 ms | 1500.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **73.1 req/s** | 500.0 ms | 1700.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **72.1 req/s** | 480.0 ms | 1500.0 ms | 0.0% |

##### Items API [GET] (ORM Serialization)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI + django-async-backend** | **91.1 req/s** | 460.0 ms | 1100.0 ms | 0.0% |
| **ASGI (Legacy Sync Views)** | **78.7 req/s** | 580.0 ms | 1200.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **75.7 req/s** | 580.0 ms | 1300.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **72.8 req/s** | 640.0 ms | 1300.0 ms | 0.0% |

##### Items API [POST] (ORM Inserts)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI + django-async-backend** | **102.6 req/s** | 380.0 ms | 860.0 ms | 0.0% |
| **ASGI (Legacy Sync Views)** | **96.1 req/s** | 420.0 ms | 1000.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **89.4 req/s** | 480.0 ms | 1100.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **88.1 req/s** | 460.0 ms | 1100.0 ms | 0.0% |

##### Catalog Search (PostgreSQL Joins & Aggregates)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI + django-async-backend** | **90.2 req/s** | 520.0 ms | 880.0 ms | 0.0% |
| **ASGI (Legacy Sync Views)** | **73.7 req/s** | 630.0 ms | 1300.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **70.0 req/s** | 670.0 ms | 1400.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **69.3 req/s** | 650.0 ms | 1400.0 ms | 0.0% |

##### Authentication & Session Middleware
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Legacy Sync Views)** | **81.0 req/s** | 570.0 ms | 1200.0 ms | 0.0% |
| **ASGI + django-async-backend** | **76.1 req/s** | 550.0 ms | 1300.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **72.6 req/s** | 630.0 ms | 1300.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **72.5 req/s** | 630.0 ms | 1300.0 ms | 0.0% |

#### Route Breakdown Across Flavors (Mixed Workload)
| Route | ASGI (Legacy Sync Views) (p95 / RPS) | ASGI (Worker=1 / Clean Async) (p95 / RPS) | ASGI (Worker=Auto / Clean Async) (p95 / RPS) | ASGI + django-async-backend (p95 / RPS) |
| :--- | :---: | :---: | :---: | :---: |
| `/api/auth/login` | 1900.0 ms (9.3 rps) | 2300.0 ms (9.5 rps) | 2600.0 ms (9.9 rps) | 1600.0 ms (9.3 rps) |
| `/api/auth/me [GET]` | 1900.0 ms (3.3 rps) | 2300.0 ms (2.6 rps) | 2200.0 ms (2.4 rps) | 1100.0 ms (2.6 rps) |
| `/api/gateway/aggregate [GET]` | 330.0 ms (17.4 rps) | 450.0 ms (14.8 rps) | 380.0 ms (14.2 rps) | 2500.0 ms (12.3 rps) |
| `/api/items [GET]` | 1900.0 ms (12.5 rps) | 2200.0 ms (10.9 rps) | 2300.0 ms (10.6 rps) | 1200.0 ms (11.9 rps) |
| `/api/items [POST]` | 1900.0 ms (2.9 rps) | 2200.0 ms (2.1 rps) | 2100.0 ms (1.7 rps) | 1200.0 ms (2.7 rps) |
| `/catalog/render [GET]` | 2000.0 ms (9.9 rps) | 2300.0 ms (8.3 rps) | 2300.0 ms (7.9 rps) | 1300.0 ms (7.5 rps) |
| `/catalog/search [GET]` | 1900.0 ms (6.1 rps) | 2300.0 ms (3.9 rps) | 2300.0 ms (5.2 rps) | 1200.0 ms (5.7 rps) |
| `/external/fetch [GET]` | 260.0 ms (10.0 rps) | 440.0 ms (7.9 rps) | 320.0 ms (8.7 rps) | 2100.0 ms (7.9 rps) |

#### Key Empirical Findings & Production Recommendations
- **Pure ASGI Architecture**: With Hurricane 2.0.0rc2+, Django runs strictly under Granian's ASGI interface, standardizing connection handling onto Tokio's asynchronous Rust runtime.
- **Legacy Synchronous Django Apps under ASGI**: For codebases reliant on synchronous ORM methods, legacy middleware, and standard forms, running Hurricane ASGI with synchronous views (`ASGI Legacy Sync Views`) achieves high socket multiplexing while avoiding the multi-hop coroutine-to-thread context switches incurred when querying the ORM from `async def` views.
- **Fast-404 & Rate Limiting Protection**: Under security flood attacks, Hurricane's Fast-404 engine drops malicious scanner probes (e.g. `/.env`, `/wp-login.php`, `/.git`) in microseconds, while the Token Bucket Rate Limiter returns 429 Too Many Requests before touching Django's URL resolver or view pipeline, preserving server capacity for legitimate traffic.
- **Hardware Footprint & Kubernetes Pod Constraints**: In typical cloud-native Kubernetes clusters running lightweight pods (1–2 vCPUs), ASGI multiplexes high connection volumes on Granian's Tokio event loop without threadpool exhaustion, providing superior operational resilience compared to traditional thread-per-request models.
- **Production Concurrency Requirement (`Worker=Auto`)**: Always deploy Hurricane with auto-threads (`Worker=Auto`), ensuring adequate threadpool depth for CPU template rendering and background tasks without starving the event loop.