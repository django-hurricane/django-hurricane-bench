### Latest Benchmark Results (2026-10-23 10:23:16 UTC)
**Django Hurricane Version:** `2.0.0rc2` | **PostgreSQL:** `17` | **Python:** `3.12`

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

#### Isolated Workload Performance (Pure Endpoint Measurement)
Workloads executed in isolation to eliminate cross-traffic contention and measure raw endpoint capability:

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
- **Isolated Relational ORM vs. Mixed Traffic Reality**: In pure, isolated database queries with zero network waiting, multi-threaded WSGI (`WSGI Worker=Auto`) achieves higher raw query throughput because OS threads execute queries directly in parallel without event-loop overhead. However, in mixed production traffic containing even modest external I/O, worker thread stalls allow `ASGI (Forced Sync Views)` to achieve higher aggregate throughput and lower median latency across the application.
- **Hardware Footprint & Kubernetes Pod Constraints (Cloud-Native Reality)**: Hardware sizing heavily influences the WSGI vs. ASGI trade-off. On large multi-core bare-metal machines, WSGI has enough threadpool depth to absorb mixed traffic without thread exhaustion. However, in production Kubernetes clusters where applications run in constrained pods (e.g. 1–2 vCPUs), WSGI's threadpool is restricted to just 5–6 threads, causing rapid thread starvation on blocking I/O. In contrast, ASGI multiplexes hundreds of concurrent connections on Granian's lightweight Tokio Rust event loop within that same constrained pod footprint, giving ASGI a decisive architectural advantage in cloud-native containerized deployments.
- **Upstream Network I/O & Microservice Fan-Out (ASGI Advantage)**: On workloads involving external API calls, slow third-party webhooks, and scatter-gather API Gateway patterns (`/external/fetch` and `/api/gateway/aggregate`), ASGI demonstrates its fundamental architectural superiority. Coroutines yield the Tokio event loop during network waits without tying up OS worker threads, keeping tail latencies flat and eliminating the thread-starvation deadlocks that severely degrade WSGI under load.
- **The 'Partial Async' Context-Switching Trap**: In workloads with mixed sync ORM and async operations, `ASGI (Forced Sync Views)` frequently matches or outperforms `ASGI (Clean Async)`. A synchronous view dispatched under ASGI incurs only a single thread context switch (`sync_to_async`), whereas `async def` views with multiple ORM queries repeatedly yield and bounce across thread boundaries and GIL locks.
- **Production Concurrency Requirement (`Worker=Auto`)**: Single-threaded deployments (`Worker=1`) for either WSGI or ASGI are highly vulnerable to blocking I/O and thread starvation under real traffic. Production deployments should always provision auto-threads (`min(32, CPU+4)`) to ensure adequate threadpool capacity for background execution and template rendering.
- **Specialized Role of Async ORM Backends (`django-async-backend`)**: Bypassing `asgiref` via `Product.async_objects` allows non-blocking `psycopg 3` connection pooling, but managing asynchronous database pools requires strict lifecycle discipline. It remains a targeted optimization for greenfield, isolated microservices rather than a drop-in default for monolithic Django applications.