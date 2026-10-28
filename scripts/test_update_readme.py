import csv
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.update_readme import (
    FLAVOR_LABELS,
    build_markdown_report,
    generate_ascii_bar,
    get_latest_archived_version,
    parse_flavor_stats,
    parse_history_scaling,
    parse_semver,
    save_archived_report,
)


class TestUpdateReadme(unittest.TestCase):
    def test_ascii_bar_generation(self):
        bar_full = generate_ascii_bar(100, 100, bar_width=10)
        self.assertEqual(bar_full, "[██████████]")

        bar_half = generate_ascii_bar(50, 100, bar_width=10)
        self.assertEqual(bar_half, "[█████     ]")

        bar_zero = generate_ascii_bar(0, 100, bar_width=10)
        self.assertEqual(bar_zero, "[          ]")

    def test_flavor_labels(self):
        self.assertIn("django-asgi", FLAVOR_LABELS)
        self.assertIn("django-asgi-auto", FLAVOR_LABELS)
        self.assertIn("django-asgi-sync", FLAVOR_LABELS)
        self.assertIn("django-asgi-async", FLAVOR_LABELS)
        self.assertEqual(FLAVOR_LABELS["django-asgi-sync"], "ASGI (Legacy Sync Views)")
        self.assertEqual(FLAVOR_LABELS["django-asgi-auto"], "ASGI (Worker=Auto / Clean Async)")
        self.assertEqual(FLAVOR_LABELS["django-asgi"], "ASGI (Worker=1 / Clean Async)")

    def test_parse_semver(self):
        v_list = ["1.9.5", "2.0.0a1", "2.0.0b1", "2.0.0rc1", "2.0.0rc2", "2.0.0", "2.0.1"]
        sorted_list = sorted(v_list, key=parse_semver)
        self.assertEqual(sorted_list, v_list)
        self.assertGreater(parse_semver("2.0.0"), parse_semver("2.0.0rc1"))
        self.assertGreater(parse_semver("2.1.0"), parse_semver("2.0.5"))

    def test_archiving_and_semver_selection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            import scripts.update_readme as ur
            orig_archive = ur.ARCHIVE_DIR
            ur.ARCHIVE_DIR = tmp_path

            try:
                # Save 2.0.0rc1 report
                f1 = save_archived_report("# Report 2.0.0rc1", "2.0.0rc1")
                self.assertTrue(f1.exists())

                # Overwrite 2.0.0rc1 report (run multiple times)
                f1_updated = save_archived_report("# Report 2.0.0rc1 updated", "2.0.0rc1")
                self.assertEqual(f1, f1_updated)
                self.assertEqual(f1.read_text(), "# Report 2.0.0rc1 updated")

                # Save 2.0.0 final
                f2 = save_archived_report("# Report 2.0.0", "2.0.0")
                self.assertTrue(f2.exists())

                latest_ver, latest_file = get_latest_archived_version()
                self.assertEqual(latest_ver, "2.0.0")
                self.assertEqual(latest_file, f2)

                # Save an older release candidate 1.9.0
                save_archived_report("# Report 1.9.0", "1.9.0")
                latest_ver_after, _ = get_latest_archived_version()
                # 2.0.0 must still remain latest semver
                self.assertEqual(latest_ver_after, "2.0.0")

            finally:
                ur.ARCHIVE_DIR = orig_archive

    def test_build_markdown_report_with_scaling_charts(self):
        sample_results = [
            {
                "flavor": "django-asgi-sync",
                "label": "ASGI (Legacy Sync Views)",
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
                    "stages": {
                        15: {"p50": 10.0, "p95": 20.0, "rps": 100.0},
                        30: {"p50": 20.0, "p95": 40.0, "rps": 200.0},
                        50: {"p50": 50.0, "p95": 90.0, "rps": 300.0},
                    },
                },
            },
            {
                "flavor": "django-asgi",
                "label": "ASGI (Worker=1 / Clean Async)",
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
                    "stages": {
                        15: {"p50": 8.0, "p95": 18.0, "rps": 120.0},
                        30: {"p50": 12.0, "p95": 24.0, "rps": 300.0},
                        50: {"p50": 20.0, "p95": 38.0, "rps": 750.0},
                    },
                },
            },
        ]
        markdown = build_markdown_report(sample_results, "2.0.0rc1")
        self.assertIn("Latest Benchmark Results", markdown)
        self.assertIn("ASGI (Legacy Sync Views)", markdown)
        self.assertIn("ASGI (Worker=1 / Clean Async)", markdown)
        self.assertIn("320.5 req/s", markdown)
        self.assertIn("750.0 req/s", markdown)
        self.assertIn("Concurrency Scaling & User Scaling Penalty", markdown)
        self.assertIn("Response Time Scaling Under User Ramp-Up", markdown)
        self.assertIn("Scaling Penalty Factor", markdown)


if __name__ == "__main__":
    unittest.main()
