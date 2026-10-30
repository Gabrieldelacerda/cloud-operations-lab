# Incident 001: Backend unavailable

## Scenario

The Python backend was intentionally stopped while Nginx remained running.
Requests to /health through the proxy returned HTTP 504.

## Investigation

From the repository root:

```bash
docker compose stop app
curl -i --max-time 5 http://127.0.0.1:8088/health
docker compose ps -a
docker compose logs --tail 20 nginx
```

The original observations below predate the shutdown improvement.
Repeating the outage with the current application can produce different
shutdown details and proxy responses.

## Original observations

- Application container stopped with exit code 137 after approximately 10 seconds.
- Docker reported `OOMKilled=false`.
- Nginx remained running.
- Requests returned HTTP 504 Gateway Time-out.
- Nginx logged `upstream timed out ... while connecting to upstream`.

## Cause

Nginx could not establish a connection to the stopped backend before the
connection timeout. The failure occurred during connection establishment,
rather than while waiting for application processing.

## Recovery

```bash
docker compose up -d --wait app
docker compose ps
curl -i --max-time 5 http://127.0.0.1:8088/health
```

The application became healthy and HTTP 200 returned without restarting Nginx.

## Shutdown improvement

The original stop duration and exit code were consistent with forced
termination after the Docker stop timeout.

Explicit SIGTERM and SIGINT handling was added. The application now exits
its request loop and closes the server when shutdown is requested.

Automated tests verify both signals using temporary containers, a three-second
stop timeout, exit code 0, `OOMKilled=false` and the clean shutdown log message.

## Verification

With the environment running:

```bash
python3 tests/http_smoke.py
bash tests/test_shutdown.sh
```

Both suites also run in the GitHub Actions Lab Checks workflow.

## Evidence

- [Clean shutdown](../../screenshots/CleanShutdown.png)
- [CI checks](../../screenshots/cichecks.png)
- [CI test results](../../screenshots/citestresults.png)
