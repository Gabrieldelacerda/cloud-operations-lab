from urllib.parse import quote
import json
import sys


def main():
    try:
        report = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        raise SystemExit(
            f"Invalid proxy summary JSON at line {error.lineno}, "
            f"column {error.colno}: {error.msg}"
        ) from None
    timing = report["request_time_seconds"]
    print("## Nginx responses in collected logs")
    print()
    print(f"- Requests captured: {report['requests']}")
    for status, count in report["statuses"].items():
        print(f"- HTTP {status}: {count}")
    if timing["samples"]:
        print(f"- p95 request time: {timing['p95']:.3f} s")
        print(f"- Maximum request time: {timing['max']:.3f} s")
        print(f"- Requests with timing data: {timing['samples']}")
    filtered = report["excluding_health"]
    filtered_timing = filtered["request_time_seconds"]
    print()
    print("### Requests excluding /health")
    print()
    print(f"- Requests captured: {filtered['requests']}")
    print(f"- Requests with timing data: {filtered_timing['samples']}")
    if filtered_timing["samples"]:
        print(f"- p95 request time: {filtered_timing['p95']:.3f} s")
        print(f"- Maximum request time: {filtered_timing['max']:.3f} s")
    else:
        print("- No request timing data in this sample.")

    timed_routes = [
        (route, stats["request_time_seconds"])
        for route, stats in report["routes"].items()
        if stats["request_time_seconds"]["samples"]
    ]
    timed_routes.sort(key=lambda item: (-item[1]["max"], item[0]))
    print()
    print("### Routes with the highest observed request times")
    print()
    if not timed_routes:
        print("No route timing data in this sample.")
    for route, timing in timed_routes[:5]:
        safe_route = quote(route, safe="/%")
        print(
            f"- `{safe_route}` | max {timing['max']:.3f} s | "
            f"p95 {timing['p95']:.3f} s | samples {timing['samples']}"
        )

    failures = [
        (route, stats)
        for route, stats in report["routes"].items()
        if route in report["server_errors_by_path"]
    ]
    failures.sort(key=lambda item: (
        -report["server_errors_by_path"][item[0]], item[0]
    ))
    print()
    print("### Routes with HTTP 5xx responses")
    print()
    if not failures:
        print("No HTTP 5xx responses outside /health in this sample.")
    for route, stats in failures[:5]:
        count = report["server_errors_by_path"][route]
        safe_route = quote(route, safe="/%")
        print(f"- `{safe_route}` | {count} of {stats['requests']} requests returned 5xx")


if __name__ == "__main__":
    main()
