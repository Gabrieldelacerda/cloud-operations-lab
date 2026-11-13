import json
import sys


def main():
    report = json.load(sys.stdin)
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


if __name__ == "__main__":
    main()
