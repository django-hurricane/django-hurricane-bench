import csv
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.update_readme import (
    FLAVOR_LABELS,
    build_markdown_report,
    generate_ascii_bar,
    parse_flavor_stats,
    parse_history_scaling,
)


class TestUpdateReadme(unittest.TestCase):
    def test_ascii_bar_generation(self):
        bar_full = generate_ascii_bar(100, 100, bar_width=10)
        self.assertEqual(bar_full, "[██████████]")

        bar_half = generate_ascii_bar(50, 100, bar_width=10)
        self.assertEqual(bar_half, "[█████     ]")

        bar_zero = generate_ascii_bar(0, 100, bar_width=10)
        self.assertEqual(bar_zero, "[          ]")

    def test_build_markdown_report(self):
        sample_results = [
            {
                "flavor": "django-wsgi",
                "label": "WSGI (Pure Sync)",
                "total_requests": 1500,
                "failures": 5,
                "error_rate": 0.33,
                "rps": 320.5,
                "median_ms": 12.0,
                "p90_ms": 45.0,
                "p95_ms": 75.0,
                "p99_ms": 150.0,
                "max_ms": 400.0,
                "routes": [
                    {"Name": "/catalog/render [GET]", "95%": "65.0", "Requests/s": "120.0"}
                ],
                "scaling": {
                    "min_users": 15,
                    "mid_users": 30,
                    "max_users": 50,
                    "low": {"p50": 10.0, "p95": 20.0, "rps": 100.0},
                    "mid": {"p50": 20.0, "p95": 40.0, "rps": 200.0},
                    "peak": {"p50": 50.0, "p95": 90.0, "rps": 300.0},
                    "penalty_factor": 4.5,
                },
            },
            {
                "flavor": "django-asgi",
                "label": "ASGI (Clean Async Views)",
                "total_requests": 3000,
                "failures": 0,
                "error_rate": 0.0,
                "rps": 750.0,
                "median_ms": 8.0,
                "p90_ms": 25.0,
                "p95_ms": 40.0,
                "p99_ms": 90.0,
                "max_ms": 200.0,
                "routes": [
                    {"Name": "/catalog/render [GET]", "95%": "35.0", "Requests/s": "240.0"}
                ],
                "scaling": {
                    "min_users": 15,
                    "mid_users": 30,
                    "max_users": 50,
                    "low": {"p50": 8.0, "p95": 18.0, "rps": 120.0},
                    "mid": {"p50": 12.0, "p95": 24.0, "rps": 300.0},
                    "peak": {"p50": 20.0, "p95": 38.0, "rps": 750.0},
                    "penalty_factor": 2.11,
                },
            },
        ]
        markdown = build_markdown_report(sample_results, "2.0.0rc1")
        self.assertIn("Latest Benchmark Results", markdown)
        self.assertIn("WSGI (Pure Sync)", markdown)
        self.assertIn("ASGI (Clean Async Views)", markdown)
        self.assertIn("320.5 req/s", markdown)
        self.assertIn("750.0 req/s", markdown)
        self.assertIn("Concurrency Scaling & User Scaling Penalty", markdown)
        self.assertIn("Latency Inflation Factor", markdown)


if __name__ == "__main__":
    unittest.main()
