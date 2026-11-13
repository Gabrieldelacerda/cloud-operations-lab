import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]


class RenderProxySummaryTests(unittest.TestCase):
    def render(self, records):
        logs = "\n".join(json.dumps(record) for record in records)
        report = subprocess.check_output(
            [sys.executable, "-B", "scripts/summarize_proxy_logs.py"],
            input=logs,
            text=True,
            cwd=ROOT,
            timeout=5,
        )
        return subprocess.check_output(
            [sys.executable, "-B", "scripts/render_proxy_summary.py"],
            input=report,
            text=True,
            cwd=ROOT,
            timeout=5,
        ).splitlines()

    def test_renders_latency_and_errors_for_a_slow_route(self):
        lines = self.render([
            {
                "uri": "/health",
                "status": 200,
                "upstream_status": "200",
                "request_time": "0.010",
            },
            {
                "uri": "/lab/slow",
                "status": 504,
                "upstream_status": "504",
                "request_time": "5.000",
            },
        ])

        latency = lines.index("### Routes with the highest observed request times")
        errors = lines.index("### Routes with HTTP 5xx responses")
        self.assertIn("- Requests captured: 2", lines)
        self.assertIn("### Requests excluding /health", lines)
        self.assertIn(
            "- `/lab/slow` | max 5.000 s | p95 5.000 s | samples 1",
            lines[latency:errors],
        )
        self.assertIn("- `/lab/slow` | 1 of 1 requests returned 5xx", lines[errors:])
        self.assertFalse(any("`/health`" in line for line in lines[latency:]))

    def test_reports_invalid_json_without_a_traceback(self):
        for report in ("", '{"requests":'):
            with self.subTest(report=report):
                result = subprocess.run(
                    [sys.executable, "-B", "scripts/render_proxy_summary.py"],
                    input=report,
                    capture_output=True,
                    text=True,
                    cwd=ROOT,
                    timeout=5,
                )

                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertTrue(
                    result.stderr.startswith("Invalid proxy summary JSON at line 1, column "),
                    result.stderr,
                )
                self.assertNotIn("Traceback", result.stderr)

    def test_rejects_json_with_the_wrong_report_structure(self):
        cases = [
            ("[]", "expected a JSON object"),
            ("{}", "missing field 'requests'"),
            ('{"requests": 0, "statuses": []}', "field 'statuses' must be of type dict"),
        ]
        for report, message in cases:
            with self.subTest(report=report):
                result = subprocess.run(
                    [sys.executable, "-B", "scripts/render_proxy_summary.py"],
                    input=report,
                    capture_output=True,
                    text=True,
                    cwd=ROOT,
                    timeout=5,
                )

                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertIn(message, result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_reads_a_saved_report_by_path(self):
        report = subprocess.check_output(
            [sys.executable, "-B", "scripts/summarize_proxy_logs.py"],
            input="",
            text=True,
            cwd=ROOT,
            timeout=5,
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "proxy summary.json"
            path.write_text(report, encoding="utf-8")
            command = [sys.executable, "-B", "scripts/render_proxy_summary.py"]

            saved = subprocess.check_output(
                [*command, str(path)], text=True, cwd=ROOT, timeout=5
            )
            piped = subprocess.check_output(
                command, input=report, text=True, cwd=ROOT, timeout=5
            )
            self.assertEqual(saved, piped)

            missing = path.with_name("missing.json")
            result = subprocess.run(
                [*command, str(missing)],
                capture_output=True,
                text=True,
                cwd=ROOT,
                timeout=5,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn(f"Could not read proxy summary from {missing}", result.stderr)

    def test_renders_an_empty_log_window(self):
        lines = self.render([])

        self.assertIn("- Requests captured: 0", lines)
        self.assertIn("No route timing data in this sample.", lines)
        self.assertIn("No HTTP 5xx responses outside /health in this sample.", lines)


if __name__ == "__main__":
    unittest.main(verbosity=2)
