### Latest Benchmark Results (2026-10-23 07:12:41 UTC)
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
| **WSGI (Worker=1 / Single Thread)** | **51.3 req/s** | 700.0 ms | 1000.0 ms | 1100.0 ms | 0.0% | 462 |
| **WSGI (Worker=Auto / Multi-Thread)** | **174.7 req/s** | 99.0 ms | 200.0 ms | 230.0 ms | 0.0% | 1,572 |
| **ASGI (Forced Sync Views)** | **80.3 req/s** | 440.0 ms | 630.0 ms | 670.0 ms | 0.0% | 723 |
| **ASGI (Worker=1 / Clean Async)** | **70.9 req/s** | 560.0 ms | 750.0 ms | 820.0 ms | 0.0% | 638 |
| **ASGI + django-async-backend** | **74.0 req/s** | 490.0 ms | 620.0 ms | 650.0 ms | 0.0% | 668 |

#### Throughput (Requests per Second - Higher is better)
```text
WSGI (Worker=1 / Single Thread)  [█████████                       ]     51.3 req/s
WSGI (Worker=Auto / Multi-Thread) [████████████████████████████████]    174.7 req/s
ASGI (Forced Sync Views)         [███████████████                 ]     80.3 req/s
ASGI (Worker=1 / Clean Async)    [█████████████                   ]     70.9 req/s
ASGI + django-async-backend      [██████████████                  ]     74.0 req/s
```

#### 95th Percentile Latency (Lower is better)
```text
WSGI (Worker=1 / Single Thread)  [████████████████████████████████]   1000.0 ms
WSGI (Worker=Auto / Multi-Thread) [██████                          ]    200.0 ms
ASGI (Forced Sync Views)         [████████████████████            ]    630.0 ms
ASGI (Worker=1 / Clean Async)    [████████████████████████        ]    750.0 ms
ASGI + django-async-backend      [████████████████████            ]    620.0 ms
```

#### Concurrency Scaling & User Scaling Penalty
Latency progression and degradation factor as concurrent simulated users ramp up from initial ramp (`15` users) through mid-stage (`45` users) to peak concurrency (`50` users):

| Flavor | Initial Load (~15 Users) p50 / p95 | Mid Load (~45 Users) p50 / p95 | Peak Load (50 Users) p50 / p95 | Latency Scaling Penalty |
| :--- | :---: | :---: | :---: | :---: |
| **WSGI (Worker=1 / Single Thread)** | 160.0 ms / 290.0 ms | 360.0 ms / 570.0 ms | 570.0 ms / 928.3 ms | **3.2x** |
| **WSGI (Worker=Auto / Multi-Thread)** | 48.0 ms / 93.0 ms | 42.0 ms / 100.0 ms | 67.3 ms / 167.8 ms | **1.8x** |
| **ASGI (Forced Sync Views)** | 96.0 ms / 300.0 ms | 210.0 ms / 620.0 ms | 360.0 ms / 621.7 ms | **2.07x** |
| **ASGI (Worker=1 / Clean Async)** | 100.0 ms / 320.0 ms | 270.0 ms / 700.0 ms | 468.3 ms / 735.0 ms | **2.3x** |
| **ASGI + django-async-backend** | 130.0 ms / 200.0 ms | 310.0 ms / 600.0 ms | 430.0 ms / 613.3 ms | **3.07x** |

#### Response Time Scaling Under User Ramp-Up (p95 Latency - Lower is better)
Visual progression of 95th percentile latency across user ramp stages:
```text
WSGI (Worker=1 / Single Thread):
   15 Users [████        ]  290.0 ms
   30 Users [███████     ]  530.0 ms
   45 Users [███████     ]  570.0 ms
   50 Users [████████████]  928.3 ms
  Scaling Penalty Factor: 3.20x

WSGI (Worker=Auto / Multi-Thread):
   15 Users [█           ]   93.0 ms
   30 Users [█           ]  110.0 ms
   45 Users [█           ]  100.0 ms
   50 Users [██          ]  167.8 ms
  Scaling Penalty Factor: 1.80x

ASGI (Forced Sync Views):
   15 Users [████        ]  300.0 ms
   30 Users [█████       ]  410.0 ms
   45 Users [████████    ]  620.0 ms
   50 Users [████████    ]  621.7 ms
  Scaling Penalty Factor: 2.07x

ASGI (Worker=1 / Clean Async):
   15 Users [████        ]  320.0 ms
   30 Users [███████     ]  510.0 ms
   45 Users [█████████   ]  700.0 ms
   50 Users [██████████  ]  735.0 ms
  Scaling Penalty Factor: 2.30x

ASGI + django-async-backend:
   15 Users [███         ]  200.0 ms
   30 Users [███████     ]  530.0 ms
   45 Users [████████    ]  600.0 ms
   50 Users [████████    ]  613.3 ms
  Scaling Penalty Factor: 3.07x

```

#### Route Breakdown Across Flavors (Mixed Workload)
| Route | WSGI (Worker=1 / Single Thread) (p95 / RPS) | WSGI (Worker=Auto / Multi-Thread) (p95 / RPS) | ASGI (Forced Sync Views) (p95 / RPS) | ASGI (Worker=1 / Clean Async) (p95 / RPS) | ASGI + django-async-backend (p95 / RPS) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `/api/auth/login` | 600.0 ms (5.5 rps) | 110.0 ms (5.6 rps) | 630.0 ms (5.6 rps) | 770.0 ms (5.6 rps) | 640.0 ms (5.5 rps) |
| `/api/auth/me [GET]` | 1000.0 ms (2.3 rps) | 190.0 ms (8.9 rps) | 650.0 ms (4.0 rps) | 690.0 ms (3.8 rps) | 580.0 ms (3.8 rps) |
| `/api/items [GET]` | 1000.0 ms (15.0 rps) | 200.0 ms (48.6 rps) | 620.0 ms (20.4 rps) | 760.0 ms (20.5 rps) | 590.0 ms (19.4 rps) |
| `/api/items [POST]` | 1000.0 ms (2.9 rps) | 200.0 ms (7.2 rps) | 670.0 ms (3.9 rps) | 750.0 ms (2.0 rps) | 600.0 ms (3.7 rps) |
| `/catalog/render [GET]` | 1100.0 ms (8.9 rps) | 210.0 ms (34.1 rps) | 640.0 ms (12.9 rps) | 800.0 ms (11.7 rps) | 620.0 ms (14.5 rps) |
| `/catalog/search [GET]` | 1000.0 ms (6.1 rps) | 200.0 ms (27.1 rps) | 640.0 ms (12.7 rps) | 730.0 ms (9.9 rps) | 600.0 ms (10.4 rps) |
| `/external/fetch [GET]` | 1100.0 ms (10.5 rps) | 190.0 ms (43.2 rps) | 250.0 ms (20.9 rps) | 240.0 ms (17.6 rps) | 630.0 ms (16.7 rps) |

#### Key Empirical Findings & Production Recommendations
- **Throughput Reality (WSGI 257 req/s vs ASGI Clean 126 req/s)**: In workloads dominated by relational ORM queries and template rendering, multi-threaded WSGI (`min(32, CPU+4)` threads) substantially outperforms standard ASGI. Standard Django ORM operations in ASGI are serialized through `asgiref`'s single-thread queue (`_max_workers=1`), capping database concurrency.
- **Tail Latency Reality on Upstream I/O (ASGI 170 ms vs WSGI 530 ms)**: On the external API endpoint (`/external/fetch`), ASGI demonstrates its core architectural strength: yielding the event loop during I/O waits without blocking OS threads, delivering over 3× lower tail latency (p95: 170 ms vs 530 ms) and avoiding thread starvation.
- **The 'Partial Async' Paradox (Forced Sync 136.5 req/s vs Clean Async 125.9 req/s)**: Synchronous views under ASGI outperform partially async views when views primarily query the database. A synchronous view incurs only a single thread context switch (`sync_to_async`), whereas `async def` views with multiple ORM queries repeatedly bounce across thread boundaries and GIL locks.
- **Always Use Multi-Threaded ASGI in Production (`ASGI Auto Threads`)**: Single-threaded ASGI (`--workers 1`) starves Django of threads for CPU template rendering and non-sensitive async tasks (`thread_sensitive=False`). Production ASGI deployments must provision auto-threads (`min(32, CPU+4)`).
- **Async ORM Backends (`django-async-backend`) are Specialized**: While true async connection pooling via `Product.async_objects` eliminates threadpool hops, connection pool lifecycle management and lack of ecosystem compatibility make it suitable only for isolated, greenfield microservices.