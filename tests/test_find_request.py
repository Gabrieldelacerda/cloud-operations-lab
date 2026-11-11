import json
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "find_request.py"
REQUEST_ID = "a" * 32


class FindRequestTests(unittest.TestCase):
    def lookup(self, request_id, log):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--stdin", request_id],
            input=log,
            capture_output=True,
            text=True,
            timeout=5,
        )

    def test_matches_raw_and_prefixed_json_by_exact_id(self):
        proxy = "nginx-1  | " + json.dumps(
            {"request_id": REQUEST_ID, "status": 200}
        )
        app = json.dumps({"request_id": REQUEST_ID, "event": "http_request"})
        other = json.dumps({"request_id": "b" * 32, "uri": f"/?id={REQUEST_ID}"})
        log = "\n".join(["app-1  | {bad json", other, proxy, app])

        result = self.lookup(REQUEST_ID, log)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [proxy, app])

    def test_finds_access_record_in_slow_backend_probe_output(self):
        record = "Access log: " + json.dumps({
            "request_id": REQUEST_ID,
            "uri": "/lab/slow?probe=example",
            "status": 504,
            "request_time": "5.005",
        })
        log = "\n".join([
            f"Response: HTTP 504, X-Request-ID: {REQUEST_ID}",
            record,
            "Error log: upstream timed out while reading response header",
        ])

        result = self.lookup(REQUEST_ID, log)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [record])

    def test_reports_no_matches(self):
        result = self.lookup(REQUEST_ID, "app-1  | Application started\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("No matching JSON entries", result.stderr)

    def test_rejects_invalid_id(self):
        result = self.lookup("invalid", "")
        self.assertEqual(result.returncode, 2)
        self.assertIn("32 lowercase hexadecimal characters", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
