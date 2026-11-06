import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent


def docker_output(*arguments):
    result = subprocess.run(
        ["docker", *arguments],
        cwd=PROJECT_DIR,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def main():
    snapshot = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "services": [],
    }
    failed = False

    for service in ("app", "nginx"):
        try:
            container_id = docker_output("compose", "ps", "-aq", service)
            if not container_id:
                snapshot["services"].append({
                    "service": service,
                    "status": "missing",
                })
                continue

            state = json.loads(docker_output(
                "inspect", "--format", "{{json .State}}", container_id
            ))
            snapshot["services"].append({
                "service": service,
                "container_id": container_id,
                "status": state["Status"],
                "exit_code": state["ExitCode"],
                "oom_killed": state["OOMKilled"],
                "health": state.get("Health"),
            })
        except (subprocess.SubprocessError, OSError, ValueError, KeyError) as error:
            failed = True
            message = str(error)
            if isinstance(error, subprocess.CalledProcessError):
                message = error.stderr.strip() or message
            snapshot["services"].append({
                "service": service,
                "collection_error": message,
            })

    print(json.dumps(snapshot, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
