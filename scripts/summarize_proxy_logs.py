import json
import sys
from collections import Counter


def summarize(lines):
    statuses = Counter()
    server_errors = Counter()

    for line in lines:
        if not line.lstrip().startswith("{"):
            _, _, line = line.partition(" | ")
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict) or "upstream_status" not in entry:
            continue

        status = entry.get("status")
        uri = entry.get("uri")
        if type(status) is not int or not 100 <= status <= 599:
            continue
        if not isinstance(uri, str) or not uri:
            continue

        statuses[status] += 1
        if status >= 500:
            server_errors[uri.split("?", 1)[0]] += 1

    return {
        "requests": sum(statuses.values()),
        "statuses": dict(sorted(statuses.items())),
        "server_errors_by_path": dict(sorted(server_errors.items())),
    }


if __name__ == "__main__":
    json.dump(summarize(sys.stdin), sys.stdout, indent=2)
    print()
