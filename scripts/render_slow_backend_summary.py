import argparse
import json
import math
import sys
from pathlib import Path


def validate_report(report):
    if not isinstance(report, dict):
        raise ValueError("the report must be a JSON object")

    requests = report.get("requests")
    if type(requests) is not int or requests < 0:
        raise ValueError("requests must be a nonnegative integer")

    statuses = report.get("statuses")
    if not isinstance(statuses, dict):
        raise ValueError("statuses must be an object")
    for status, count in statuses.items():
        if (
            len(status) != 3
            or not status.isascii()
            or not status.isdigit()
            or not 100 <= int(status) <= 599
        ):
            raise ValueError("statuses must use HTTP status codes as keys")
        if type(count) is not int or count < 0:
            raise ValueError("status counts must be nonnegative integers")
    if sum(statuses.values()) != requests:
        raise ValueError("status counts must add up to requests")

    timing = report.get("request_time_seconds")
    if not isinstance(timing, dict):
        raise ValueError("request_time_seconds must be an object")

    samples = timing.get("samples")
    if type(samples) is not int or not 0 <= samples <= requests:
        raise ValueError("timing samples must be between zero and requests")

    maximum = timing.get("max")
    if samples == 0:
        if maximum is not None:
            raise ValueError("maximum request time must be null without samples")
    elif (
        type(maximum) not in (int, float)
        or maximum < 0
        or not math.isfinite(maximum)
    ):
        raise ValueError("maximum request time must be a finite nonnegative number")


def main():
    parser = argparse.ArgumentParser(
        description="Render a slow-backend JSON summary as Markdown."
    )
    parser.add_argument(
        "report", nargs="?", type=Path,
        help="JSON report path; read stdin when omitted",
    )
    args = parser.parse_args()

    try:
        source = (
            args.report.read_text(encoding="utf-8")
            if args.report is not None
            else sys.stdin.read()
        )
    except (OSError, UnicodeError) as error:
        print(f"Could not read slow backend summary: {error}", file=sys.stderr)
        return 1

    try:
        report = json.loads(source)
    except json.JSONDecodeError as error:
        print(
            f"Could not parse slow backend summary: invalid JSON "
            f"at line {error.lineno}, column {error.colno}.",
            file=sys.stderr,
        )
        return 1

    try:
        validate_report(report)
    except ValueError as error:
        print(f"Invalid slow backend summary: {error}.", file=sys.stderr)
        return 1

    timing = report["request_time_seconds"]

    print("## Slow backend timeout probe")
    print()
    if report["requests"]:
        print(f"- Probe requests captured: {report['requests']}")
        print(f"- HTTP 504 responses: {report['statuses'].get('504', 0)}")
        if timing["samples"]:
            print(f"- Maximum Nginx request time: {timing['max']:.3f} s")
    else:
        print("No proxy access records were captured for this probe.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
