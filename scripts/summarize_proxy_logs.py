import json
import math
import sys
from collections import Counter, defaultdict


def summarize_durations(durations):
    ordered = sorted(durations)
    samples = len(ordered)
    if not samples:
        return {"samples": 0, "p95": None, "max": None}

    p95_rank = (95 * samples + 99) // 100
    return {"samples": samples, "p95": ordered[p95_rank - 1], "max": ordered[-1]}


def summarize(lines):
    statuses = Counter()
    server_errors = Counter()
    durations = []
    non_health_durations = []
    non_health_requests = 0
    route_requests = Counter()
    route_durations = defaultdict(list)

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

        path = uri.split("?", 1)[0]
        is_health = path == "/health"

        statuses[status] += 1
        if not is_health:
            non_health_requests += 1
            route_requests[path] += 1
        try:
            duration = float(entry.get("request_time"))
        except (TypeError, ValueError, OverflowError):
            pass
        else:
            if math.isfinite(duration) and duration >= 0:
                durations.append(duration)
                if not is_health:
                    non_health_durations.append(duration)
                    route_durations[path].append(duration)
        if status >= 500:
            server_errors[path] += 1

    return {
        "request_time_seconds": summarize_durations(durations),
        "excluding_health": {
            "requests": non_health_requests,
            "request_time_seconds": summarize_durations(non_health_durations),
        },
        "requests": sum(statuses.values()),
        "statuses": dict(sorted(statuses.items())),
        "server_errors_by_path": dict(sorted(server_errors.items())),
        "routes": {
            path: {
                "requests": route_requests[path],
                "request_time_seconds": summarize_durations(route_durations[path]),
            }
            for path in sorted(route_requests)
        },
    }


if __name__ == "__main__":
    json.dump(summarize(sys.stdin), sys.stdout, indent=2)
    print()
