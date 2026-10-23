#!/usr/bin/env python3
import csv
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPORTS_DIR = Path("reports")
ARCHIVE_DIR = Path("archive")
README_PATH = Path("README.md")
START_MARKER = "<!-- BENCHMARK_START -->"
END_MARKER = "<!-- BENCHMARK_END -->"

FLAVOR_LABELS = {
    "django-wsgi": "WSGI (Worker=1 / Single Thread)",
    "django-wsgi-auto": "WSGI (Worker=Auto / Multi-Thread)",
    "django-asgi-sync": "ASGI (Forced Sync Views)",
    "django-asgi": "ASGI (Worker=1 / Clean Async)",
    "django-asgi-auto": "ASGI (Worker=Auto / Clean Async)",
    "django-asgi-async": "ASGI + django-async-backend",
}

ISOLATED_WORKLOAD_LABELS = {
    "gateway_aggregate": "API Gateway / BFF (Scatter-Gather Fan-Out)",
    "catalog_render": "Catalog Render (DTL Template Engine)",
    "external_fetch": "External Fetch (Upstream API I/O)",
    "items_get": "Items API [GET] (ORM Serialization)",
    "items_post": "Items API [POST] (ORM Inserts)",
    "catalog_search": "Catalog Search (PostgreSQL Joins & Aggregates)",
    "auth": "Authentication & Session Middleware",
}


def parse_semver(v: str):
    """
    Parses a semantic version string into a comparable tuple.
    Handles standard versions (1.2.3), release candidates (2.0.0rc1),
    betas (2.0.0b1), alphas (2.0.0a1), and dev releases.
    """
    if not v:
        return ((0,), 0, 0)
    clean_v = str(v).strip().lstrip("v")
    match = re.match(
        r"^(\d+(?:\.\d+)*)(?:[-._]?(a|alpha|b|beta|rc|c|pre|preview|dev)?[-._]?(\d*))?",
        clean_v,
        re.IGNORECASE,
    )
    if not match:
        return ((0,), 0, 0)
    nums_part, tag, tag_num = match.groups()
    nums = tuple(int(x) for x in nums_part.split("."))

    if not tag:
        tag_prio = 4  # Final GA release
        tag_n = 0
    else:
        tag = tag.lower()
        if tag in ("dev",):
            tag_prio = 0
        elif tag in ("a", "alpha"):
            tag_prio = 1
        elif tag in ("b", "beta"):
            tag_prio = 2
        elif tag in ("rc", "c", "pre", "preview"):
            tag_prio = 3
        else:
            tag_prio = 1
        tag_n = int(tag_num) if tag_num else 0

    return (nums, tag_prio, tag_n)


def parse_history_scaling(flavor_name, csv_prefix=None):
    file_prefix = csv_prefix or flavor_name
    csv_path = REPORTS_DIR / f"{file_prefix}_stats_history.csv"
    if not csv_path.exists():
        return None

    rows = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("Name") == "Aggregated" and r.get("User Count"):
                try:
                    u = int(r["User Count"])
                    if u > 0 and r.get("50%") not in ("N/A", "", None):
                        rows.append({
                            "users": u,
                            "p50": float(r["50%"]),
                            "p95": float(r["95%"]),
                            "rps": float(r.get("Requests/s", 0) or 0),
                        })
                except (ValueError, TypeError):
                    continue

    if not rows:
        return None

    user_levels = sorted(list({r["users"] for r in rows}))
    if not user_levels:
        return None

    min_users = user_levels[0]
    max_users = user_levels[-1]
    mid_users = user_levels[len(user_levels) // 2]

    stages = {}
    for u in user_levels:
        matches = [r for r in rows if r["users"] == u]
        if matches:
            avg_p50 = sum(m["p50"] for m in matches) / len(matches)
            avg_p95 = sum(m["p95"] for m in matches) / len(matches)
            last_rps = matches[-1]["rps"]
            stages[u] = {
                "p50": round(avg_p50, 1),
                "p95": round(avg_p95, 1),
                "rps": round(last_rps, 1),
            }

    low_tier = stages.get(min_users, {"p50": 0.0, "p95": 0.0, "rps": 0.0})
    mid_tier = stages.get(mid_users, {"p50": 0.0, "p95": 0.0, "rps": 0.0})
    peak_tier = stages.get(max_users, {"p50": 0.0, "p95": 0.0, "rps": 0.0})

    initial_p95 = low_tier["p95"]
    peak_p95 = peak_tier["p95"]
    penalty_factor = round((peak_p95 / initial_p95), 2) if initial_p95 > 0 else 1.0

    return {
        "min_users": min_users,
        "mid_users": mid_users,
        "max_users": max_users,
        "low": low_tier,
        "mid": mid_tier,
        "peak": peak_tier,
        "penalty_factor": penalty_factor,
        "stages": stages,
    }


def parse_flavor_stats(flavor_name, csv_prefix=None):
    file_prefix = csv_prefix or flavor_name
    csv_path = REPORTS_DIR / f"{file_prefix}_stats.csv"
    if not csv_path.exists():
        return None

    aggregated = None
    routes = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name", "")
            if name == "Aggregated":
                aggregated = row
            else:
                routes.append(row)

    if not aggregated:
        return None

    def to_float(val, default=0.0):
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def to_int(val, default=0):
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    total_requests = to_int(aggregated.get("Request Count"))
    failure_count = to_int(aggregated.get("Failure Count"))
    error_rate = (failure_count / total_requests * 100) if total_requests > 0 else 0.0

    stats = {
        "flavor": flavor_name,
        "label": FLAVOR_LABELS.get(flavor_name, flavor_name),
        "total_requests": total_requests,
        "failures": failure_count,
        "error_rate": round(error_rate, 2),
        "rps": round(to_float(aggregated.get("Requests/s")), 1),
        "median_ms": round(to_float(aggregated.get("50%")), 1),
        "p90_ms": round(to_float(aggregated.get("90%")), 1),
        "p95_ms": round(to_float(aggregated.get("95%")), 1),
        "p99_ms": round(to_float(aggregated.get("99%")), 1),
        "max_ms": round(to_float(aggregated.get("Max Response Time")), 1),
        "routes": routes,
        "scaling": parse_history_scaling(flavor_name, csv_prefix),
    }
    return stats


def parse_isolated_workload_stats(flavors):
    """Finds and parses isolated workload runs (e.g. reports/<flavor>_<workload>_stats.csv)."""
    isolated_results = {}
    for workload_key, workload_label in ISOLATED_WORKLOAD_LABELS.items():
        workload_data = []
        for f in flavors:
            prefix = f"{f}_{workload_key}"
            stat = parse_flavor_stats(f, csv_prefix=prefix)
            if stat:
                workload_data.append(stat)
        if workload_data:
            isolated_results[workload_key] = {
                "label": workload_label,
                "data": workload_data,
            }
    return isolated_results


def generate_ascii_bar(val, max_val, bar_width=32, fill_char="█"):
    if max_val <= 0:
        return "[" + (" " * bar_width) + "]"
    fill_len = int(round((val / max_val) * bar_width))
    fill_len = max(1 if val > 0 else 0, min(fill_len, bar_width))
    empty_len = bar_width - fill_len
    return "[" + (fill_char * fill_len) + (" " * empty_len) + "]"


def build_markdown_report(results, hurricane_version, isolated_results=None):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = []
    lines.append(f"### Latest Benchmark Results ({timestamp})")
    lines.append(f"**Django Hurricane Version:** `{hurricane_version}` | **PostgreSQL:** `17` | **Python:** `3.12`\n")

    # Runtime Architecture Table
    lines.append("#### Server & Worker Runtime Architecture")
    lines.append("| Flavor | Server Interface | Worker Processes | Server Threads | Event Loop | App Concurrency Model | DB Pool |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    lines.append("| **WSGI (Worker=1)** | Granian WSGI | 1 | 1 | None | Single OS thread (In-thread) | Sync psycopg (4 conns) |")
    lines.append("| **WSGI (Auto Threads)** | Granian WSGI | 1 | `min(32, CPU+4)` (6–12) | None | Multi-threaded (In-thread) | Sync psycopg (4 conns) |")
    lines.append("| **ASGI (Forced Sync)** | Granian ASGI | 1 | 1 | Tokio (`mt`) | `asgiref` single-thread queue | Sync psycopg (4 conns) |")
    lines.append("| **ASGI (Clean Async)** | Granian ASGI | 1 | 1 | Tokio (`mt`) | Native async views + threadpool DTL | Sync psycopg (4 conns) |")
    lines.append("| **ASGI (Auto Threads)** | Granian ASGI | 1 | `min(32, CPU+4)` (6–12) | Tokio (`mt`) | Native async views + multi-thread DTL | Sync psycopg (4 conns) |")
    lines.append("| **ASGI + DAB** | Granian ASGI | 1 | 1 | Tokio (`mt`) | True async ORM (`async_objects`) | Async psycopg-pool (5–50 conns) |")
    lines.append("")

    # Aggregate Table
    lines.append("#### Aggregate Performance Metrics (Mixed Workload)")
    lines.append("| Flavor | Throughput | Median (p50) | 95th (p95) | 99th (p99) | Error Rate | Requests |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    for r in results:
        lines.append(
            f"| **{r['label']}** | **{r['rps']} req/s** | {r['median_ms']} ms | {r['p95_ms']} ms | {r['p99_ms']} ms | {r['error_rate']}% | {r['total_requests']:,} |"
        )
    lines.append("")

    # Visual Bar Charts
    max_rps = max(r["rps"] for r in results) if results else 1.0
    max_p95 = max(r["p95_ms"] for r in results) if results else 1.0

    lines.append("#### Throughput (Requests per Second - Higher is better)")
    lines.append("```text")
    for r in results:
        bar = generate_ascii_bar(r["rps"], max_rps)
        lines.append(f"{r['label']:<32} {bar} {r['rps']:>8.1f} req/s")
    lines.append("```\n")

    lines.append("#### 95th Percentile Latency (Lower is better)")
    lines.append("```text")
    for r in results:
        bar = generate_ascii_bar(r["p95_ms"], max_p95)
        lines.append(f"{r['label']:<32} {bar} {r['p95_ms']:>8.1f} ms")
    lines.append("```\n")

    # Concurrency Scaling & Scaling Charts
    scaling_results = [r for r in results if r.get("scaling")]
    if scaling_results:
        min_u = scaling_results[0]["scaling"]["min_users"]
        mid_u = scaling_results[0]["scaling"]["mid_users"]
        max_u = scaling_results[0]["scaling"]["max_users"]
        lines.append("#### Concurrency Scaling & User Scaling Penalty")
        lines.append(
            f"Latency progression and degradation factor as concurrent simulated users ramp up from initial ramp (`{min_u}` users) through mid-stage (`{mid_u}` users) to peak concurrency (`{max_u}` users):\n"
        )
        lines.append(
            f"| Flavor | Initial Load (~{min_u} Users) p50 / p95 | Mid Load (~{mid_u} Users) p50 / p95 | Peak Load ({max_u} Users) p50 / p95 | Latency Scaling Penalty |"
        )
        lines.append("| :--- | :---: | :---: | :---: | :---: |")
        for r in scaling_results:
            sc = r["scaling"]
            lines.append(
                f"| **{r['label']}** | {sc['low']['p50']} ms / {sc['low']['p95']} ms | {sc['mid']['p50']} ms / {sc['mid']['p95']} ms | {sc['peak']['p50']} ms / {sc['peak']['p95']} ms | **{sc['penalty_factor']}x** |"
            )
        lines.append("")

        # Visual User Ramp-up Latency Scaling Chart
        all_stage_p95s = [
            st["p95"]
            for r in scaling_results
            for st in r["scaling"].get("stages", {}).values()
            if st.get("p95")
        ]
        max_stage_p95 = max(all_stage_p95s) if all_stage_p95s else 100.0

        lines.append("#### Response Time Scaling Under User Ramp-Up (p95 Latency - Lower is better)")
        lines.append("Visual progression of 95th percentile latency across user ramp stages:")
        lines.append("```text")
        for r in scaling_results:
            lines.append(f"{r['label']}:")
            stages = r["scaling"].get("stages", {})
            for u in sorted(stages.keys()):
                p95_val = stages[u]["p95"]
                bar = generate_ascii_bar(p95_val, max_stage_p95, bar_width=12)
                lines.append(f"  {u:3d} Users {bar} {p95_val:6.1f} ms")
            penalty = r["scaling"].get("penalty_factor", 1.0)
            lines.append(f"  Scaling Penalty Factor: {penalty:.2f}x\n")
        lines.append("```\n")

    # Isolated Workloads Section (if executed and available)
    if isolated_results:
        lines.append("#### Isolated Workload Performance (Pure Endpoint Measurement)")
        lines.append("Workloads executed in isolation to eliminate cross-traffic contention and measure raw endpoint capability:\n")
        for workload_key, w_info in isolated_results.items():
            lines.append(f"##### {w_info['label']}")
            lines.append("| Flavor | Throughput | Median (p50) | 95th (p95) | Error Rate |")
            lines.append("| :--- | :---: | :---: | :---: | :---: |")
            w_sorted = sorted(w_info["data"], key=lambda x: x["rps"], reverse=True)
            for d in w_sorted:
                lines.append(f"| **{d['label']}** | **{d['rps']} req/s** | {d['median_ms']} ms | {d['p95_ms']} ms | {d['error_rate']}% |")
            lines.append("")

    # Per route analysis (Mixed workload)
    lines.append("#### Route Breakdown Across Flavors (Mixed Workload)")
    route_names = sorted(list({row.get("Name") for r in results for row in r["routes"]}))
    if route_names:
        lines.append("| Route | " + " | ".join(f"{r['label']} (p95 / RPS)" for r in results) + " |")
        lines.append("| :--- | " + " | ".join([":---:"] * len(results)) + " |")
        for route in route_names:
            cols = [f"`{route}`"]
            for r in results:
                matched = next((x for x in r["routes"] if x.get("Name") == route), None)
                if matched:
                    p95 = round(float(matched.get("95%", 0)), 1)
                    rps = round(float(matched.get("Requests/s", 0)), 1)
                    cols.append(f"{p95} ms ({rps} rps)")
                else:
                    cols.append("-")
            lines.append("| " + " | ".join(cols) + " |")
        lines.append("")

    # Architectural Analysis & Recommendations
    lines.append("#### Key Empirical Findings & Production Recommendations")
    lines.append("- **Isolated Relational ORM vs. Mixed Traffic Reality**: In pure, isolated database queries with zero network waiting, multi-threaded WSGI (`WSGI Worker=Auto`) achieves higher raw query throughput because OS threads execute queries directly in parallel without event-loop overhead. However, in mixed production traffic containing even modest external I/O, worker thread stalls allow `ASGI (Forced Sync Views)` to achieve higher aggregate throughput and lower median latency across the application.")
    lines.append("- **Hardware Footprint & Kubernetes Pod Constraints (Cloud-Native Reality)**: Hardware sizing heavily influences the WSGI vs. ASGI trade-off. On large multi-core bare-metal machines, WSGI has enough threadpool depth to absorb mixed traffic without thread exhaustion. However, in production Kubernetes clusters where applications run in constrained pods (e.g. 1–2 vCPUs), WSGI's threadpool is restricted to just 5–6 threads, causing rapid thread starvation on blocking I/O. In contrast, ASGI multiplexes hundreds of concurrent connections on Granian's lightweight Tokio Rust event loop within that same constrained pod footprint, giving ASGI a decisive architectural advantage in cloud-native containerized deployments.")
    lines.append("- **Upstream Network I/O & Microservice Fan-Out (ASGI Advantage)**: On workloads involving external API calls, slow third-party webhooks, and scatter-gather API Gateway patterns (`/external/fetch` and `/api/gateway/aggregate`), ASGI demonstrates its fundamental architectural superiority. Coroutines yield the Tokio event loop during network waits without tying up OS worker threads, keeping tail latencies flat and eliminating the thread-starvation deadlocks that severely degrade WSGI under load.")
    lines.append("- **The 'Partial Async' Context-Switching Trap**: In workloads with mixed sync ORM and async operations, `ASGI (Forced Sync Views)` frequently matches or outperforms `ASGI (Clean Async)`. A synchronous view dispatched under ASGI incurs only a single thread context switch (`sync_to_async`), whereas `async def` views with multiple ORM queries repeatedly yield and bounce across thread boundaries and GIL locks.")
    lines.append("- **Production Concurrency Requirement (`Worker=Auto`)**: Single-threaded deployments (`Worker=1`) for either WSGI or ASGI are highly vulnerable to blocking I/O and thread starvation under real traffic. Production deployments should always provision auto-threads (`min(32, CPU+4)`) to ensure adequate threadpool capacity for background execution and template rendering.")
    lines.append("- **Specialized Role of Async ORM Backends (`django-async-backend`)**: Bypassing `asgiref` via `Product.async_objects` allows non-blocking `psycopg 3` connection pooling, but managing asynchronous database pools requires strict lifecycle discipline. It remains a targeted optimization for greenfield, isolated microservices rather than a drop-in default for monolithic Django applications.")

    return "\n".join(lines)


def save_archived_report(report_markdown: str, hurricane_version: str) -> Path:
    """Writes or overwrites the markdown report in the archive folder."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_file = ARCHIVE_DIR / f"benchmark-{hurricane_version}.md"
    with open(archive_file, "w", encoding="utf-8") as f:
        f.write(report_markdown)
    return archive_file


def get_latest_archived_version() -> tuple:
    """Scans archive/ for benchmark-*.md and returns (latest_version_str, file_path)."""
    if not ARCHIVE_DIR.exists():
        return None, None
    files = list(ARCHIVE_DIR.glob("benchmark-*.md"))
    if not files:
        return None, None

    def get_version(p: Path):
        m = re.match(r"^benchmark-(.+)\.md$", p.name)
        return m.group(1) if m else "0.0.0"

    latest_file = max(files, key=lambda p: parse_semver(get_version(p)))
    return get_version(latest_file), latest_file


def update_readme(hurricane_version):
    flavors = [
        "django-wsgi",
        "django-wsgi-auto",
        "django-asgi-sync",
        "django-asgi",
        "django-asgi-auto",
        "django-asgi-async",
    ]
    results = []
    for f in flavors:
        stat = parse_flavor_stats(f)
        if stat:
            results.append(stat)

    if not results:
        print("[update_readme] No stats found in reports/. Exiting.")
        return

    isolated_results = parse_isolated_workload_stats(flavors)
    current_report = build_markdown_report(results, hurricane_version, isolated_results)

    # 1. Archive the current report (replace if existing release)
    archive_path = save_archived_report(current_report, hurricane_version)
    print(f"[update_readme] Successfully saved release report to {archive_path}")

    # 2. Determine whether to update README.md based on Semantic Versioning
    latest_ver, latest_path = get_latest_archived_version()
    current_semver = parse_semver(hurricane_version)
    latest_semver = parse_semver(latest_ver) if latest_ver else current_semver

    report_to_publish = current_report
    if latest_ver and current_semver < latest_semver:
        print(
            f"[update_readme] Current version ({hurricane_version}) is older than latest archived release ({latest_ver})."
            f" Reading latest report from {latest_path} for README.md."
        )
        with open(latest_path, "r", encoding="utf-8") as f:
            report_to_publish = f.read()

    # 3. Update README.md
    if not README_PATH.exists():
        print(f"[update_readme] {README_PATH} does not exist.")
        return

    with open(README_PATH, "r", encoding="utf-8") as f:
        readme = f.read()

    start_idx = readme.find(START_MARKER)
    end_idx = readme.find(END_MARKER)

    if start_idx != -1 and end_idx != -1:
        new_readme = (
            readme[: start_idx + len(START_MARKER)]
            + "\n\n"
            + report_to_publish
            + "\n\n"
            + readme[end_idx:]
        )
    else:
        new_readme = readme + f"\n\n{START_MARKER}\n\n{report_to_publish}\n\n{END_MARKER}\n"

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_readme)

    print(f"[update_readme] Successfully updated {README_PATH} with latest release report ({latest_ver or hurricane_version}).")


if __name__ == "__main__":
    version = os.environ.get("HURRICANE_VERSION", "2.0.0rc1")
    if len(sys.argv) > 1:
        version = sys.argv[1]
    update_readme(version)
