import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from log_records import parse_log_record


class LogRecordTests(unittest.TestCase):
    def test_accepts_supported_log_formats(self):
        record = {"request_id": "a" * 32, "status": 504}
        payload = json.dumps(record)

        for line in (
            payload,
            "nginx-1  | " + payload,
            "Access log: " + payload,
        ):
            with self.subTest(line=line):
                self.assertEqual(parse_log_record(line), record)

    def test_accepts_whitespace_around_raw_json(self):
        self.assertEqual(
            parse_log_record('  {"status": 200}\n'),
            {"status": 200},
        )

    def test_ignores_plain_text_and_malformed_json(self):
        for line in (
            "",
            "app-1  | Application listening on port 8000",
            "nginx-1  | [error] upstream timed out",
            "Access log: {invalid",
            '{"status":',
        ):
            with self.subTest(line=line):
                self.assertIsNone(parse_log_record(line))

    def test_ignores_json_values_that_are_not_objects(self):
        for value in (None, True, 200, "message", [{"status": 200}]):
            with self.subTest(value=value):
                self.assertIsNone(parse_log_record(json.dumps(value)))

    def test_preserves_separator_inside_json_strings(self):
        record = {"uri": "/?value=left | right", "status": 200}
        payload = json.dumps(record)

        for line in (payload, "nginx-1  | " + payload):
            with self.subTest(line=line):
                self.assertEqual(parse_log_record(line), record)


if __name__ == "__main__":
    unittest.main(verbosity=2)
