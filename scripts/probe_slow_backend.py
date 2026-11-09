import json
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from uuid import uuid4


PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_URL = "http://127.0.0.1:8088"


def main():
    path = f"/lab/slow?probe={uuid4().hex}"

    try:
        response = urlopen(f"{BASE_URL}{path}", timeout=12)
    except HTTPError as error:
        response = error
    except URLError as error:
        raise SystemExit(f"Could not reach Nginx: {error}") from error

    with response:
        status = response.status
        request_id = response.headers.get("X-Request-ID")
        response.read()

    if status != 504 or not request_id:
        raise SystemExit(f"Expected HTTP 504 with X-Request-ID, got HTTP {status}")

    print(f"Response: HTTP {status}, X-Request-ID: {request_id}", flush=True)

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        logs = subprocess.run(
            [
                "docker", "compose", "logs", "--no-color", "--no-log-prefix",
                "--tail", "100", "nginx",
            ],
            cwd=PROJECT_DIR,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        ).stdout

        access_entry = None
        timeout_entry = None
        for line in logs.splitlines():
            line = line.strip()
            if path not in line:
                continue

            if line.startswith("{"):
                entry = json.loads(line)
                if entry.get("request_id") == request_id and entry.get("uri") == path:
                    access_entry = entry
            elif (
                "upstream timed out" in line
                and "while reading response header from upstream" in line
            ):
                timeout_entry = line

        if access_entry is not None and timeout_entry is not None:
            if access_entry.get("status") != 504:
                raise SystemExit("The matching access log did not record HTTP 504")

            print("Access log:", json.dumps(access_entry))
            print("Error log:", timeout_entry)
            return

        time.sleep(0.2)

    raise SystemExit("Matching access log or upstream read-timeout message not found")


if __name__ == "__main__":
    main()
