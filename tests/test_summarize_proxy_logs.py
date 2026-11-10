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
            {"requests": 0, "statuses": {}, "server_errors_by_path": {}},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
