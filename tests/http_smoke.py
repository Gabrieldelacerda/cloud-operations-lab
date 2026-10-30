import json
import os
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen


BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8088").rstrip("/")


class HttpSmokeTests(unittest.TestCase):
    def request_json(self, path, expected_status):
        try:
            response = urlopen(f"{BASE_URL}{path}", timeout=5)
        except HTTPError as error:
            response = error

        with response:
            self.assertEqual(response.status, expected_status)
            self.assertEqual(response.headers.get_content_type(), "application/json")
            return json.load(response)

    def test_application_identity(self):
        payload = self.request_json("/", 200)
        self.assertEqual(payload["service"], "cloud-operations-lab")

    def test_health(self):
        payload = self.request_json("/health", 200)
        self.assertEqual(payload, {"status": "ok"})

    def test_health_with_query_string(self):
        payload = self.request_json("/health?source=smoke", 200)
        self.assertEqual(payload, {"status": "ok"})

    def test_unknown_route(self):
        payload = self.request_json("/does-not-exist", 404)
        self.assertEqual(payload, {"error": "Not found"})


if __name__ == "__main__":
    print(f"Testing {BASE_URL}", flush=True)
    unittest.main(verbosity=2)
