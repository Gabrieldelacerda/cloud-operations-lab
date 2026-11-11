import json
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/summarize_proxy_logs.py"


class ProxyLogSummaryTests(unittest.TestCase):
    def summarize(self, lines):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="\n".join(lines),
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return json.loads(result.stdout)

    def test_counts_proxy_responses_and_groups_errors_without_query_strings(self):
        summary = self.summarize([
            'nginx-1  | {"status":200,"uri":"/health","upstream_status":"200"}',
            '{"status":404,"uri":"/missing","upstream_status":"404"}',
            '{"status":504,"uri":"/lab/slow?probe=one","upstream_status":"504"}',
            '{"status":502,"uri":"/lab/slow?probe=two","upstream_status":"502"}',
            'app-1  | {"status":200,"uri":"/health","event":"http_request"}',
            'nginx-1  | [error] upstream timed out',
            'nginx-1  | {invalid json',
        ])
        self.assertEqual(summary["requests"], 4)
        self.assertEqual(summary["statuses"], {"200": 1, "404": 1, "502": 1, "504": 1})
        self.assertEqual(summary["server_errors_by_path"], {"/lab/slow": 2})

    def test_empty_summary_when_no_proxy_access_logs_are_present(self):
        self.assertEqual(
            self.summarize(["", "app-1  | Application started"]),
            {
                "requests": 0,
                "statuses": {},
                "server_errors_by_path": {},
                "routes": {},
                "request_time_seconds": {"samples": 0, "p95": None, "max": None},
                "excluding_health": {
                    "requests": 0,
                    "request_time_seconds": {"samples": 0, "p95": None, "max": None},
                },
            },
        )


    def test_latency_uses_nearest_rank_and_skips_invalid_values(self):
        values = [str(value) for value in range(1, 21)] + ["-", "NaN", "-1"]
        summary = self.summarize([
            json.dumps({
                "status": 200,
                "uri": "/health",
                "upstream_status": "200",
                "request_time": value,
            })
            for value in values
        ])
        self.assertEqual(summary["requests"], 23)
        self.assertEqual(
            summary["request_time_seconds"],
            {"samples": 20, "p95": 19.0, "max": 20.0},
        )


    def test_p95_excludes_health_even_with_a_query_string(self):
        health = json.dumps({
            "status": 200, "uri": "/health", "upstream_status": "200",
            "request_time": "0.010",
        })
        slow = json.dumps({
            "status": 504, "uri": "/lab/slow", "upstream_status": "504",
            "request_time": "5.000",
        })
        summary = self.summarize(
            [health] * 18 + [health.replace("/health", "/health?source=smoke"), slow]
        )

        self.assertEqual(summary["requests"], 20)
        self.assertEqual(
            summary["request_time_seconds"],
            {"samples": 20, "p95": 0.01, "max": 5.0},
        )
        self.assertEqual(
            summary["excluding_health"],
            {
                "requests": 1,
                "request_time_seconds": {"samples": 1, "p95": 5.0, "max": 5.0},
            },
        )


    def test_groups_route_timings_without_query_strings(self):
        records = [
            ("/health?source=smoke", "0.010"),
            ("/lab/slow?probe=1", "4.000"),
            ("/lab/slow?probe=2", "5.000"),
            ("/", "-"),
        ]
        summary = self.summarize([
            json.dumps({
                "status": 200,
                "uri": uri,
                "upstream_status": "200",
                "request_time": duration,
            })
            for uri, duration in records
        ])

        self.assertEqual(summary["routes"], {
            "/": {
                "requests": 1,
                "request_time_seconds": {"samples": 0, "p95": None, "max": None},
            },
            "/lab/slow": {
                "requests": 2,
                "request_time_seconds": {"samples": 2, "p95": 5.0, "max": 5.0},
            },
        })


if __name__ == "__main__":
    unittest.main(verbosity=2)
