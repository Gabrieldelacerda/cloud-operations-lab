import json
import sys


def main():
    try:
        report = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(
            f"Could not parse slow backend summary: invalid JSON "
            f"at line {error.lineno}, column {error.colno}.",
            file=sys.stderr,
        )
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
