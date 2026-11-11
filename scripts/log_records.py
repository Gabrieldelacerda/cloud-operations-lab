import json


def parse_log_record(line):
    """Read a JSON object from a raw, Compose, or probe log line."""
    message = line.removeprefix("Access log: ")
    if message == line and not line.lstrip().startswith("{"):
        _, separator, payload = line.partition(" | ")
        if separator:
            message = payload

    try:
        record = json.loads(message)
    except ValueError:
        return None

    return record if isinstance(record, dict) else None
