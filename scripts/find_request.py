import argparse
import re
import subprocess
import sys

from log_records import parse_log_record


def matching_lines(lines, request_id):
    for line in lines:
        record = parse_log_record(line)
        if record is not None and record.get("request_id") == request_id:
            yield line.rstrip("\r\n")


def main():
    parser = argparse.ArgumentParser(
        description="Find JSON log entries for an Nginx request ID."
    )
    parser.add_argument("request_id")
    parser.add_argument("--stdin", action="store_true", help="Read saved logs from stdin")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{32}", args.request_id):
        parser.error("request_id must contain 32 lowercase hexadecimal characters")

    if args.stdin:
        lines = sys.stdin
    else:
        try:
            result = subprocess.run(
                ["docker", "compose", "logs", "--no-color", "--tail", "100", "nginx", "app"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=10,
                check=True,
            )
        except (OSError, subprocess.SubprocessError) as error:
            detail = getattr(error, "stdout", None)
            print(f"Could not read Compose logs: {detail or error}", file=sys.stderr)
            return 2
        lines = result.stdout.splitlines()

    found = False
    for line in matching_lines(lines, args.request_id):
        print(line)
        found = True

    if not found:
        print(f"No matching JSON entries for {args.request_id}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
