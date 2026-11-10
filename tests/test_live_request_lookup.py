import subprocess
import sys
import unittest
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
LOOKUP = ROOT / "scripts" / "find_request.py"


class LiveRequestLookupTests(unittest.TestCase):
    def test_health_request_is_found_in_both_services(self):
        with urlopen("http://127.0.0.1:8088/health", timeout=5) as response:
            self.assertEqual(response.status, 200)
            request_id = response.headers.get("X-Request-ID", "")
            self.assertRegex(request_id, r"^[0-9a-f]{32}$")
            response.read()

        result = subprocess.run(
            [sys.executable, str(LOOKUP), request_id],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        for service in ("nginx", "app"):
            with self.subTest(service=service):
                self.assertRegex(
                    result.stdout,
                    rf"(?m)^(?:\S+-)?{service}-\d+\s+\|",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
