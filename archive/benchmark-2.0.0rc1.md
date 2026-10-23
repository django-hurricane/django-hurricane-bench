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
- **Throughput Reality (WSGI 257 req/s vs ASGI Clean 126 req/s)**: In workloads dominated by relational ORM queries and template rendering, multi-threaded WSGI (`min(32, CPU+4)` threads) substantially outperforms standard ASGI. Standard Django ORM operations in ASGI are serialized through `asgiref`'s single-thread queue (`_max_workers=1`), capping database concurrency.
- **Tail Latency Reality on Upstream I/O (ASGI 170 ms vs WSGI 530 ms)**: On the external API endpoint (`/external/fetch`), ASGI demonstrates its core architectural strength: yielding the event loop during I/O waits without blocking OS threads, delivering over 3× lower tail latency (p95: 170 ms vs 530 ms) and avoiding thread starvation.
- **The 'Partial Async' Paradox (Forced Sync 136.5 req/s vs Clean Async 125.9 req/s)**: Synchronous views under ASGI outperform partially async views when views primarily query the database. A synchronous view incurs only a single thread context switch (`sync_to_async`), whereas `async def` views with multiple ORM queries repeatedly bounce across thread boundaries and GIL locks.
- **Always Use Multi-Threaded ASGI in Production (`ASGI Auto Threads`)**: Single-threaded ASGI (`--workers 1`) starves Django of threads for CPU template rendering and non-sensitive async tasks (`thread_sensitive=False`). Production ASGI deployments must provision auto-threads (`min(32, CPU+4)`).
- **Async ORM Backends (`django-async-backend`) are Specialized**: While true async connection pooling via `Product.async_objects` eliminates threadpool hops, connection pool lifecycle management and lack of ecosystem compatibility make it suitable only for isolated, greenfield microservices.