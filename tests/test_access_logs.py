import json
import math
import os
import subprocess
import time
import unittest
import uuid
from datetime import datetime
from urllib.error import HTTPError
from urllib.request import urlopen


BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8088").rstrip("/")


class AccessLogTests(unittest.TestCase):
    def check_request(self, route, expected_status, suffix=""):
        marker = uuid.uuid4().hex
        path = f"{route}?log_test={marker}{suffix}"

        try:
            response = urlopen(f"{BASE_URL}{path}", timeout=5)
        except HTTPError as error:
            response = error

        with response:
            self.assertEqual(response.status, expected_status)
            request_id = response.headers.get("X-Request-ID")
            self.assertIsNotNone(request_id)
            self.assertRegex(request_id, r"^[0-9a-f]{32}$")
            response.read()

        entry = self.wait_for_entry(marker, path)
        self.assertEqual(entry["request_id"], request_id)
        self.assertEqual(entry["method"], "GET")
        self.assertEqual(entry["uri"], path)
        self.assertIs(type(entry["status"]), int)
        self.assertEqual(entry["status"], expected_status)
        self.assertEqual(entry["upstream_status"], str(expected_status))
        self.assertTrue(entry["upstream_addr"])
        self.assertNotEqual(entry["upstream_addr"], "-")
        self.assertIsNotNone(datetime.fromisoformat(entry["time"]).tzinfo)

        for field in (
            "request_time",
            "upstream_connect_time",
            "upstream_header_time",
            "upstream_response_time",
        ):
            with self.subTest(field=field):
                value = float(entry[field])
                self.assertTrue(math.isfinite(value))
                self.assertGreaterEqual(value, 0)

        return request_id

    def wait_for_entry(self, marker, path):
        deadline = time.monotonic() + 10

        while time.monotonic() < deadline:
            # Larger tails omitted fresh entries on the lab's Docker Engine.
            result = subprocess.run(
                [
                    "docker", "compose", "logs",
                    "--no-color", "--no-log-prefix",
                    "--tail", "100", "nginx",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )

            for line in result.stdout.splitlines():
                if marker not in line or not line.startswith("{"):
                    continue
                entry = json.loads(line)
                if entry.get("uri") == path:
                    return entry

            time.sleep(0.2)

        self.fail(f"No matching JSON access log found for {path}")

    def test_successful_request(self):
        self.check_request("/health", 200)

    def test_unknown_route(self):
        self.check_request("/does-not-exist", 404)

    def test_json_escaping(self):
        self.check_request("/health", 200, '&value="quoted"\\path')

    def test_distinct_request_ids(self):
        first = self.check_request("/health", 200)
        second = self.check_request("/health", 200)
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    print(f"Checking Nginx access logs for {BASE_URL}", flush=True)
    unittest.main(verbosity=2)
