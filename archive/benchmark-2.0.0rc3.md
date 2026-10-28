### Latest Benchmark Results (2026-10-28 15:56:23 UTC)
**Django Hurricane Version:** `2.0.0rc3` (Pure ASGI) | **PostgreSQL:** `17` | **Python:** `3.12`

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
| **ASGI (Legacy Sync Views)** | **26.4 req/s** | 3600.0 ms | 6500.0 ms | 6800.0 ms | 0.0% | 1,187 |
| **ASGI (Worker=1 / Clean Async)** | **40.4 req/s** | 2200.0 ms | 4200.0 ms | 4300.0 ms | 0.0% | 1,818 |
| **ASGI (Worker=Auto / Clean Async)** | **124.6 req/s** | 960.0 ms | 1100.0 ms | 1100.0 ms | 0.0% | 5,615 |
| **ASGI + django-async-backend** | **40.2 req/s** | 2600.0 ms | 4100.0 ms | 4100.0 ms | 0.0% | 1,812 |

#### Throughput (Requests per Second - Higher is better)
```text
ASGI (Legacy Sync Views)         [███████                         ]     26.4 req/s
ASGI (Worker=1 / Clean Async)    [██████████                      ]     40.4 req/s
ASGI (Worker=Auto / Clean Async) [████████████████████████████████]    124.6 req/s
ASGI + django-async-backend      [██████████                      ]     40.2 req/s
```

#### 95th Percentile Latency (Lower is better)
```text
ASGI (Legacy Sync Views)         [████████████████████████████████]   6500.0 ms
ASGI (Worker=1 / Clean Async)    [█████████████████████           ]   4200.0 ms
ASGI (Worker=Auto / Clean Async) [█████                           ]   1100.0 ms
ASGI + django-async-backend      [████████████████████            ]   4100.0 ms
```

#### Concurrency Scaling & User Scaling Penalty
Latency progression and degradation factor as concurrent simulated users ramp up from initial ramp (`12` users) through mid-stage (`87` users) to peak concurrency (`150` users):

| Flavor | Initial Load (~12 Users) p50 / p95 | Mid Load (~87 Users) p50 / p95 | Peak Load (150 Users) p50 / p95 | Latency Scaling Penalty |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Legacy Sync Views)** | 320.0 ms / 850.0 ms | 1300.0 ms / 1600.0 ms | 2943.5 ms / 5373.9 ms | **6.32x** |
| **ASGI (Worker=1 / Clean Async)** | 120.0 ms / 320.0 ms | 770.0 ms / 1000.0 ms | 1947.8 ms / 3608.7 ms | **11.28x** |
| **ASGI (Worker=Auto / Clean Async)** | 45.0 ms / 130.0 ms | 140.0 ms / 490.0 ms | 637.4 ms / 1083.0 ms | **8.33x** |
| **ASGI + django-async-backend** | 190.0 ms / 300.0 ms | 730.0 ms / 1200.0 ms | 2117.4 ms / 3673.9 ms | **12.25x** |

#### Response Time Scaling Under User Ramp-Up (p95 Latency - Lower is better)
Visual progression of 95th percentile latency across user ramp stages:
```text
ASGI (Legacy Sync Views):
   12 Users [██          ]  850.0 ms
   24 Users [██          ]  840.0 ms
   36 Users [██          ]  920.0 ms
   37 Users [███         ] 1365.0 ms
   62 Users [████        ] 1600.0 ms
   87 Users [████        ] 1600.0 ms
   90 Users [██████      ] 2866.7 ms
  115 Users [████████    ] 3500.0 ms
  140 Users [████████    ] 3500.0 ms
  150 Users [████████████] 5373.9 ms
  Scaling Penalty Factor: 6.32x

ASGI (Worker=1 / Clean Async):
   12 Users [█           ]  320.0 ms
   24 Users [█           ]  660.0 ms
   36 Users [██          ]  800.0 ms
   37 Users [██          ]  918.3 ms
   62 Users [██          ]  970.0 ms
   87 Users [██          ] 1000.0 ms
   90 Users [████        ] 1955.6 ms
  115 Users [█████       ] 2200.0 ms
  140 Users [█████       ] 2200.0 ms
  150 Users [████████    ] 3608.7 ms
  Scaling Penalty Factor: 11.28x

ASGI (Worker=Auto / Clean Async):
   12 Users [█           ]  130.0 ms
   24 Users [█           ]  160.0 ms
   36 Users [█           ]  190.0 ms
   37 Users [█           ]  203.3 ms
   62 Users [█           ]  380.0 ms
   87 Users [█           ]  490.0 ms
   90 Users [█           ]  620.0 ms
  115 Users [█           ]  630.0 ms
  140 Users [██          ]  800.0 ms
  150 Users [██          ] 1083.0 ms
  Scaling Penalty Factor: 8.33x

ASGI + django-async-backend:
   12 Users [█           ]  300.0 ms
   24 Users [█           ]  500.0 ms
   36 Users [█           ]  570.0 ms
   37 Users [██          ]  963.3 ms
   62 Users [██          ]  990.0 ms
   87 Users [███         ] 1200.0 ms
   90 Users [█████       ] 2088.9 ms
  115 Users [██████      ] 2500.0 ms
  140 Users [██████      ] 2500.0 ms
  150 Users [████████    ] 3673.9 ms
  Scaling Penalty Factor: 12.25x

```

#### Fast-404 & Rate Limiting Attack Defense Performance
Evaluation of Hurricane's security engines: comparing clean baseline traffic against a massive flood of dictionary attacks (Fast-404 early drop in microseconds) and rate-limited abuse (429 Too Many Requests):

| Flavor | Clean Baseline RPS | Under Attack RPS | Clean Median | Attack Median | Throughput Capacity Factor |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **ASGI (Legacy Sync Views)** | **26.3 req/s** | **54.6 req/s** | 3600.0 ms | 760.0 ms | **2.08x** |
| **ASGI (Worker=1 / Clean Async)** | **41.5 req/s** | **100.6 req/s** | 2400.0 ms | 4.0 ms | **2.42x** |
| **ASGI (Worker=Auto / Clean Async)** | **124.0 req/s** | **276.2 req/s** | 960.0 ms | 5.0 ms | **2.23x** |
| **ASGI + django-async-backend** | **42.8 req/s** | **101.3 req/s** | 2500.0 ms | 9.0 ms | **2.37x** |

#### Isolated Workload Performance (Pure Endpoint Measurement)
Workloads executed in isolation to eliminate cross-traffic contention and measure raw endpoint capability:

##### Security Flood: Fast-404 Dictionary Attack & 429 Rate Limiter Abuse
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Worker=Auto / Clean Async)** | **276.2 req/s** | 5.0 ms | 1000.0 ms | 0.0% |
| **ASGI + django-async-backend** | **101.3 req/s** | 9.0 ms | 2900.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **100.6 req/s** | 4.0 ms | 2900.0 ms | 0.0% |
| **ASGI (Legacy Sync Views)** | **54.6 req/s** | 760.0 ms | 5000.0 ms | 2.19% |

##### Clean Baseline: Valid Traffic with Security Protection (No Flood)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Worker=Auto / Clean Async)** | **124.0 req/s** | 960.0 ms | 1100.0 ms | 0.0% |
| **ASGI + django-async-backend** | **42.8 req/s** | 2500.0 ms | 4000.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **41.5 req/s** | 2400.0 ms | 3900.0 ms | 0.0% |
| **ASGI (Legacy Sync Views)** | **26.3 req/s** | 3600.0 ms | 6200.0 ms | 0.0% |

##### API Gateway / BFF (Scatter-Gather Fan-Out)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Worker=Auto / Clean Async)** | **98.6 req/s** | 1200.0 ms | 1400.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **23.1 req/s** | 4200.0 ms | 7200.0 ms | 0.0% |
| **ASGI + django-async-backend** | **23.0 req/s** | 4300.0 ms | 7200.0 ms | 0.0% |
| **ASGI (Legacy Sync Views)** | **11.8 req/s** | 7100.0 ms | 12000.0 ms | 0.0% |

##### Catalog Render (DTL Template Engine)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Worker=Auto / Clean Async)** | **96.9 req/s** | 1300.0 ms | 1400.0 ms | 0.0% |
| **ASGI (Legacy Sync Views)** | **94.2 req/s** | 1300.0 ms | 1500.0 ms | 0.0% |
| **ASGI + django-async-backend** | **89.1 req/s** | 1400.0 ms | 1600.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **88.7 req/s** | 1400.0 ms | 1600.0 ms | 0.0% |

##### External Fetch (Upstream API I/O)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Worker=Auto / Clean Async)** | **124.8 req/s** | 970.0 ms | 1100.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **20.0 req/s** | 5200.0 ms | 8600.0 ms | 0.0% |
| **ASGI (Legacy Sync Views)** | **19.8 req/s** | 5200.0 ms | 8900.0 ms | 0.0% |
| **ASGI + django-async-backend** | **19.8 req/s** | 5200.0 ms | 8500.0 ms | 0.0% |

##### Items API [GET] (ORM Serialization)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Worker=Auto / Clean Async)** | **159.6 req/s** | 730.0 ms | 800.0 ms | 0.0% |
| **ASGI (Legacy Sync Views)** | **151.1 req/s** | 780.0 ms | 860.0 ms | 0.0% |
| **ASGI + django-async-backend** | **145.0 req/s** | 830.0 ms | 900.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **143.7 req/s** | 830.0 ms | 920.0 ms | 0.0% |

##### Items API [POST] (ORM Inserts)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Worker=Auto / Clean Async)** | **194.6 req/s** | 570.0 ms | 630.0 ms | 0.0% |
| **ASGI (Legacy Sync Views)** | **186.9 req/s** | 600.0 ms | 670.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **176.9 req/s** | 640.0 ms | 710.0 ms | 0.0% |
| **ASGI + django-async-backend** | **176.8 req/s** | 640.0 ms | 710.0 ms | 0.0% |

##### Catalog Search (PostgreSQL Joins & Aggregates)
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Worker=Auto / Clean Async)** | **142.4 req/s** | 840.0 ms | 910.0 ms | 0.0% |
| **ASGI (Legacy Sync Views)** | **113.3 req/s** | 1000.0 ms | 1200.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **109.4 req/s** | 1100.0 ms | 1200.0 ms | 0.0% |
| **ASGI + django-async-backend** | **108.5 req/s** | 1200.0 ms | 1300.0 ms | 0.0% |

##### Authentication & Session Middleware
| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |
| :--- | :---: | :---: | :---: | :---: |
| **ASGI (Legacy Sync Views)** | **169.0 req/s** | 680.0 ms | 750.0 ms | 0.0% |
| **ASGI (Worker=Auto / Clean Async)** | **155.7 req/s** | 740.0 ms | 830.0 ms | 0.0% |
| **ASGI (Worker=1 / Clean Async)** | **149.5 req/s** | 790.0 ms | 870.0 ms | 0.0% |
| **ASGI + django-async-backend** | **141.7 req/s** | 840.0 ms | 930.0 ms | 0.0% |

#### Route Breakdown Across Flavors (Mixed Workload)
| Route | ASGI (Legacy Sync Views) (p95 / RPS) | ASGI (Worker=1 / Clean Async) (p95 / RPS) | ASGI (Worker=Auto / Clean Async) (p95 / RPS) | ASGI + django-async-backend (p95 / RPS) |
| :--- | :---: | :---: | :---: | :---: |
| `/api/auth/login` | 6100.0 ms (4.5 rps) | 4100.0 ms (5.2 rps) | 1100.0 ms (8.9 rps) | 3900.0 ms (5.3 rps) |
| `/api/auth/me [GET]` | 6300.0 ms (1.0 rps) | 4200.0 ms (1.8 rps) | 1100.0 ms (6.6 rps) | 4100.0 ms (1.8 rps) |
| `/api/gateway/aggregate [GET]` | 6500.0 ms (6.1 rps) | 4300.0 ms (8.9 rps) | 1100.0 ms (30.4 rps) | 4100.0 ms (8.8 rps) |
| `/api/items [GET]` | 6600.0 ms (4.6 rps) | 4200.0 ms (7.5 rps) | 1100.0 ms (23.2 rps) | 4100.0 ms (7.5 rps) |
| `/api/items [POST]` | 6500.0 ms (1.1 rps) | 4200.0 ms (2.2 rps) | 1100.0 ms (7.1 rps) | 4100.0 ms (1.7 rps) |
| `/catalog/render [GET]` | 6500.0 ms (3.4 rps) | 4300.0 ms (5.6 rps) | 1100.0 ms (18.9 rps) | 4000.0 ms (5.6 rps) |
| `/catalog/search [GET]` | 6500.0 ms (2.6 rps) | 4200.0 ms (3.3 rps) | 1100.0 ms (11.8 rps) | 4000.0 ms (3.6 rps) |
| `/external/fetch [GET]` | 6600.0 ms (3.0 rps) | 4300.0 ms (5.8 rps) | 1100.0 ms (17.7 rps) | 4100.0 ms (5.9 rps) |

#### Key Empirical Findings & Production Recommendations
- **Pure ASGI Architecture**: With Hurricane 2.0.0rc2+, Django runs strictly under Granian's ASGI interface, standardizing connection handling onto Tokio's asynchronous Rust runtime.
- **Legacy Synchronous Django Apps under ASGI**: For codebases reliant on synchronous ORM methods, legacy middleware, and standard forms, running Hurricane ASGI with synchronous views (`ASGI Legacy Sync Views`) achieves high socket multiplexing while avoiding the multi-hop coroutine-to-thread context switches incurred when querying the ORM from `async def` views.
- **Fast-404 & Rate Limiting Protection**: Under security flood attacks, Hurricane's Fast-404 engine drops malicious scanner probes (e.g. `/.env`, `/wp-login.php`, `/.git`) in microseconds, while the Token Bucket Rate Limiter returns 429 Too Many Requests before touching Django's URL resolver or view pipeline, preserving server capacity for legitimate traffic.
- **Hardware Footprint & Kubernetes Pod Constraints**: In typical cloud-native Kubernetes clusters running lightweight pods (1–2 vCPUs), ASGI multiplexes high connection volumes on Granian's Tokio event loop without threadpool exhaustion, providing superior operational resilience compared to traditional thread-per-request models.
- **Production Concurrency Requirement (`Worker=Auto`)**: Always deploy Hurricane with auto-threads (`Worker=Auto`), ensuring adequate threadpool depth for CPU template rendering and background tasks without starving the event loop.