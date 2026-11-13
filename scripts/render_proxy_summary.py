from urllib.parse import quote
import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Render a proxy summary as Markdown."
    )
    parser.add_argument(
        "report",
        nargs="?",
        type=Path,
        help="Path to the JSON report. Defaults to standard input.",
    )
    args = parser.parse_args()

    try:
        if args.report is None:
            report = json.load(sys.stdin)
        else:
            report = json.loads(args.report.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        location = args.report if args.report is not None else "standard input"
        raise SystemExit(f"Could not read proxy summary from {location}: {error}") from None
    except json.JSONDecodeError as error:
        raise SystemExit(
            f"Invalid proxy summary JSON at line {error.lineno}, "
            f"column {error.colno}: {error.msg}"
        ) from None

    if not isinstance(report, dict):
        raise SystemExit("Invalid proxy summary: expected a JSON object.")

    required_fields = {
        "requests": int,
        "statuses": dict,
        "request_time_seconds": dict,
        "excluding_health": dict,
        "routes": dict,
        "server_errors_by_path": dict,
    }
    for field, expected_type in required_fields.items():
        if field not in report:
            raise SystemExit(f"Invalid proxy summary: missing field '{field}'.")
        if type(report[field]) is not expected_type:
            raise SystemExit(
                f"Invalid proxy summary: field '{field}' "
                f"must be of type {expected_type.__name__}."
            )
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
