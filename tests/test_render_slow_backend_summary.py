import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts" / "render_slow_backend_summary.py"


class RenderSlowBackendSummaryTests(unittest.TestCase):
    def render(self, requests, statuses, samples, maximum):
        report = {
            "requests": requests,
            "statuses": statuses,
            "request_time_seconds": {"samples": samples, "max": maximum},
        }
        return subprocess.check_output(
            [sys.executable, "-B", str(RENDERER)],
            input=json.dumps(report),
            text=True,
            timeout=5,
        ).splitlines()

    def test_renders_a_504_with_the_observed_duration(self):
        lines = self.render(1, {"504": 1}, 1, 5.006)

        self.assertIn("## Slow backend timeout probe", lines)
        self.assertIn("- Probe requests captured: 1", lines)
        self.assertIn("- HTTP 504 responses: 1", lines)
        self.assertIn("- Maximum Nginx request time: 5.006 s", lines)

    def test_preserves_the_504_count_when_timing_is_missing(self):
        lines = self.render(1, {"504": 1}, 0, None)

        self.assertIn("- HTTP 504 responses: 1", lines)
        self.assertFalse(
            any(line.startswith("- Maximum Nginx request time:") for line in lines)
        )

    def test_explains_when_no_access_records_were_captured(self):
        lines = self.render(0, {}, 0, None)

        self.assertIn("No proxy access records were captured for this probe.", lines)


if __name__ == "__main__":
    unittest.main(verbosity=2)
