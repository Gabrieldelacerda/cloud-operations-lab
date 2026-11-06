# Cloud Operations Lab

A local lab for investigating HTTP availability issues, documenting incident
recovery and testing operational improvements with Python, Nginx and Docker Compose.

## Environment

- Python HTTP application with `/` and `/health` endpoints.
- Nginx reverse proxy accessible at `127.0.0.1:8088`.
- Application and proxy healthchecks with startup dependencies.
- Non-root application container with SIGTERM and SIGINT handling.
- Read-only application filesystem, dropped capabilities and no-new-privileges.
- Container log rotation.
- JSON request logs correlated across Nginx and the application using request IDs.

The Python application listens on port 8000 inside the Compose network.

## Run locally

Requirements: Git, Docker Engine, Docker Compose, Bash and curl.
Python 3 is also required for the HTTP, log-correlation and recovery tests.

```bash
git clone https://github.com/Gabrieldelacerda/cloud-operations-lab.git
cd cloud-operations-lab
docker compose up -d --build --wait --wait-timeout 60
docker compose ps
curl -i --max-time 5 http://127.0.0.1:8088/health
```

Expected health response: HTTP 200 with `{"status": "ok"}`.
When using a VM, execute these commands inside that VM.

## Troubleshooting

Collect container status, recent logs and the HTTP health response:

```bash
bash scripts/diagnose.sh
```

For individual checks:

```bash
docker compose ps -a
docker compose logs --tail=100
curl -i --max-time 5 http://127.0.0.1:8088/health
```

Use container status, logs and HTTP responses together to investigate a
failure before making changes.

See the [operations guide](docs/operations.md) for healthchecks, container
restrictions, log rotation and recovery procedures.

## Request correlation

Nginx returns an `X-Request-ID` response header and forwards the generated
ID to the application. Both services record it in their JSON request logs.

```bash
curl --silent --show-error --include --write-out '\n' \
  'http://127.0.0.1:8088/health?source=correlation'
docker compose logs --no-color --no-log-prefix --tail 100 nginx
docker compose logs --no-color --no-log-prefix --tail 100 app
```

Match the response header to the `request_id` in both logs.
Direct application healthchecks bypass Nginx and have a null request ID.
A proxy failure before reaching the application may have no application entry.

See the [logging guide](docs/logging.md) for field definitions,
HTTP failure investigation and observed log-retrieval limitations.

## Automated tests

With the environment running:

```bash
python3 tests/http_smoke.py
python3 tests/test_access_logs.py
bash tests/test_shutdown.sh
bash tests/test_recovery.sh
```

The HTTP suite checks application identity, health responses, query strings
and unknown routes through Nginx.

The log suite checks correlation between response headers, proxy logs and
application logs, including HTTP 404 responses. It also checks JSON escaping,
distinct request IDs, timestamps and upstream timing fields.

The shutdown suite creates isolated temporary containers and verifies
SIGTERM and SIGINT handling, exit code 0, the OOM indicator and shutdown logs.
Temporary containers are removed after testing.

The recovery suite temporarily stops the lab application, expects HTTP
502 or 504, restores the backend and reruns the HTTP checks. It also verifies
that Nginx was neither restarted nor replaced.

The recovery test interrupts the current lab. Its exit handler attempts
to start the application again if the test fails or is interrupted.
See the [operations guide](docs/operations.md#test-backend-outage-and-recovery)
for cleanup limitations and manual recovery.

## Continuous integration

[Lab Checks](https://github.com/Gabrieldelacerda/cloud-operations-lab/actions/workflows/lab-checks.yml)
runs on pushes, pull requests and manual execution.

The workflow validates shell syntax and Compose configuration, builds the
environment, runs HTTP, log-correlation, recovery and shutdown tests,
and executes environment diagnostics.

Before cleanup, it collects container status and service logs and uploads
them as a `lab-diagnostics-<run-id>-<attempt>` artifact with seven-day retention.
Collection, upload and cleanup are attempted even after test failures.

Download the artifact from the workflow run's Summary page to inspect
`container-status.txt` and `compose.log` after the containers are removed.

![GitHub Actions recovery validation](screenshots/verifylab.png)

## Incident investigation

[Incident 001: Backend unavailable](docs/incidents/001-backend-unavailable.md)

The original controlled outage produced HTTP 504 while Nginx remained running.
Logs identified a connection timeout to the stopped backend. Starting the
application restored HTTP 200 without restarting Nginx.

The investigation also exposed slow shutdown, which led to explicit signal
handling and automated shutdown tests. Backend outage and recovery are now
tested locally and in CI.

## Evidence

- [Structured Nginx access logs](screenshots/NginxAccessLogs.png)
- [Application 404 log](screenshots/404log.png)
- [Backend outage log](screenshots/BEOutage.png)
- [Backend outage and recovery](screenshots/testrecovery.png)
- [Environment diagnostics in CI](screenshots/Environment_Diagnostics_CI.png)
- [Application restrictions](screenshots/AppRestrictions.png)
- [Healthchecks and log rotation](screenshots/HealthChecks_LogRotation.png)
- [Running services and HTTP 200](screenshots/composeps.png)
- [Clean application shutdown](screenshots/CleanShutdown.png)
- [HTTP and shutdown test results](screenshots/citestresults.png)
- [Docker image build](screenshots/DockerBuild.png)
- [Environment startup](screenshots/DockerCompose.png)

## Stop the environment

```bash
docker compose down
```

## Scope

This is a local learning environment using Python's standard-library HTTP
server. Recovery is explicitly performed by the test script; the lab does
not implement automatic failover. Cloud infrastructure and additional
incident scenarios are planned extensions.
