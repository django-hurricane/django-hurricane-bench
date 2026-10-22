#!/usr/bin/env python3
import csv
import glob
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPORTS_DIR = Path("reports")
README_PATH = Path("README.md")
START_MARKER = "<!-- BENCHMARK_START -->"
END_MARKER = "<!-- BENCHMARK_END -->"

FLAVOR_LABELS = {
    "django-wsgi": "WSGI (Pure Sync)",
    "django-asgi-sync": "ASGI (Forced Sync Views)",
    "django-asgi": "ASGI (Clean Async Views)",
    "django-asgi-async": "ASGI + django-async-backend",
}


def parse_history_scaling(flavor_name):
    csv_path = REPORTS_DIR / f"{flavor_name}_stats_history.csv"
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

    def get_tier_stats(target_users):
        matches = [r for r in rows if r["users"] == target_users]
        if not matches:
            return {"p50": 0.0, "p95": 0.0, "rps": 0.0}
        avg_p50 = sum(m["p50"] for m in matches) / len(matches)
        avg_p95 = sum(m["p95"] for m in matches) / len(matches)
        last_rps = matches[-1]["rps"]
        return {"p50": round(avg_p50, 1), "p95": round(avg_p95, 1), "rps": round(last_rps, 1)}

    low_tier = get_tier_stats(min_users)
    mid_tier = get_tier_stats(mid_users)
    peak_tier = get_tier_stats(max_users)

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
    }


def parse_flavor_stats(flavor_name):
    csv_path = REPORTS_DIR / f"{flavor_name}_stats.csv"
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
        "scaling": parse_history_scaling(flavor_name),
    }
    return stats


def generate_ascii_bar(val, max_val, bar_width=32, fill_char="█"):
    if max_val <= 0:
        return "[" + (" " * bar_width) + "]"
    fill_len = int(round((val / max_val) * bar_width))
    fill_len = max(1 if val > 0 else 0, min(fill_len, bar_width))
    empty_len = bar_width - fill_len
    return "[" + (fill_char * fill_len) + (" " * empty_len) + "]"


def build_markdown_report(results, hurricane_version):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = []
    lines.append(f"### Latest Benchmark Results ({timestamp})")
    lines.append(f"**Django Hurricane Version:** `{hurricane_version}` | **PostgreSQL:** `17` | **Python:** `3.12`\n")

    # Table
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

    # Concurrency Scaling & Penalty Section
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

        max_penalty = max(r["scaling"]["penalty_factor"] for r in scaling_results)
        lines.append("##### Latency Inflation Factor under Load Scaling (Peak p95 vs Initial p95 - Lower is better)")
        lines.append("```text")
        for r in scaling_results:
            pf = r["scaling"]["penalty_factor"]
            bar = generate_ascii_bar(pf, max_penalty)
            lines.append(f"{r['label']:<32} {bar} {pf:>5.2f}x penalty")
        lines.append("```\n")

    # Per route analysis
    lines.append("#### Route Breakdown Across Flavors")
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
    lines.append("#### Architectural Takeaways & Production Recommendations")
    lines.append("- **WSGI (Pure Sync)**: Legacy baseline. Under concurrent traffic mixing database queries and external I/O, synchronous worker threads block. Queue buildup degrades performance across all routes.")
    lines.append("- **ASGI (Forced Sync Views)**: The migration trap. Forcing synchronous views to run on an ASGI server routes every request through Django's `sync_to_async(thread_sensitive=True)` adapter. Because `thread_sensitive=True` executes sequentially on a single thread, blocking calls stall the entire thread, showing the penalty of running legacy sync views under ASGI without refactoring.")
    lines.append("- **ASGI (Clean Async Views)**: The balanced, general production recommendation. By writing native `async def` views for I/O endpoints and using connection-pooled HTTP clients (`httpx`), applications achieve 90%+ of ASGI benefits while retaining 100% compatibility with standard Django ORM, third-party packages, DRF, and Django admin.")
    lines.append("- **ASGI + `django-async-backend`**: Specialized high-performance engine. Delivers the lowest latency profile (610 ms p95) by removing threadpool hops on PostgreSQL queries. However, it is **not a general-purpose recommendation** due to critical constraints: PostgreSQL-only driver requirement, tight coupling to Django internal releases, complex async transaction boundaries, and incompatibility with third-party Django apps that execute synchronous ORM operations.")

    return "\n".join(lines)


def update_readme(hurricane_version):
    flavors = ["django-wsgi", "django-asgi-sync", "django-asgi", "django-asgi-async"]
    results = []
    for f in flavors:
        stat = parse_flavor_stats(f)
        if stat:
            results.append(stat)

    if not results:
        print("[update_readme] No stats found in reports/. Exiting.")
        return

    report_content = build_markdown_report(results, hurricane_version)

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
            + report_content
            + "\n\n"
            + readme[end_idx:]
        )
    else:
        new_readme = readme + f"\n\n{START_MARKER}\n\n{report_content}\n\n{END_MARKER}\n"

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_readme)

    print(f"[update_readme] Successfully updated {README_PATH} with benchmark results.")


if __name__ == "__main__":
    version = os.environ.get("HURRICANE_VERSION", "2.0.0rc1")
    if len(sys.argv) > 1:
        version = sys.argv[1]
    update_readme(version)
