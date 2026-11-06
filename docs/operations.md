# Operating the lab

## Start and validate

Run commands from the repository root:

```bash
docker compose up -d --build --wait --wait-timeout 60
python3 tests/http_smoke.py
docker compose ps
```

Both services should report healthy.

## Collect diagnostics

```bash
bash scripts/diagnose.sh
```

The script validates Compose configuration, lists running and stopped
containers, checks service health, prints recent logs and requests the
health endpoint through Nginx.

Exit code 0 requires successful checks, both services running and healthy,
and a successful HTTP health request. Missing, stopped or unhealthy
containers cause exit code 1.

The script continues collecting available evidence after a failed check.
It does not restart or modify containers.

[Diagnostics running in CI](../screenshots/Environment_Diagnostics_CI.png)

## Inspect healthcheck history

```bash
python3 scripts/health_snapshot.py
```

The JSON snapshot includes capture time and, for each service:

- Container ID and process status.
- Container exit code and OOM indicator.
- Health status and consecutive failure count.
- Recent probe timestamps, exit codes and output retained by Docker.

Empty probe output is expected when a successful check produces no text.
The probe exit code determines whether that check succeeded.

The script reports missing containers explicitly. Exit code 0 means
collection succeeded; it does not mean every service is healthy.
Collection errors produce JSON error records and exit code 1.

This command is read-only and does not run new health probes.

## Healthchecks

The application healthcheck requests its own `/health` endpoint.
The Nginx healthcheck requests `/health` through the proxy, checking
connectivity to the application as well.

HTTP responses can recover before Docker's next scheduled probe updates
the container health status.

An unhealthy status alone does not trigger a container restart.
The `unless-stopped` policy handles container exits, not healthcheck failures.

## Test backend outage and recovery

Run only against the local lab; this temporarily interrupts the application:

```bash
bash tests/test_recovery.sh
```

The test:

1. Confirms both containers are running and the HTTP smoke tests pass.
2. Stops the application and expects HTTP 502 or 504 through Nginx.
3. Starts the same application container and polls for HTTP 200.
4. Reruns the four HTTP smoke tests.
5. Waits for both container healthchecks to report healthy.
6. Checks that Nginx retains its container ID and start time.

The observed local outage returned HTTP 504. Recovery restored HTTP 200
and healthy container states without restarting Nginx.

[Backend outage and recovery evidence](../screenshots/testrecovery.png)

The script explicitly restores the backend; this is not automatic failover.
If the test fails or receives SIGINT or SIGTERM, its exit handler attempts
to start the application again. That cleanup attempt does not verify
application health and cannot run after SIGKILL or host failure.

If restoration fails, recover manually and validate:

```bash
docker compose up -d --wait --wait-timeout 60 app
python3 tests/http_smoke.py
bash scripts/diagnose.sh
```

## Test diagnostic failure detection

```bash
bash tests/test_diagnostics.sh
```

This test also temporarily stops the application. It verifies that:

- Diagnostics succeed with healthy services.
- A stopped backend produces exit code 1 and an application failure message.
- Diagnostics succeed again after restoration.

Verbose diagnostic output is captured temporarily and printed if a check
fails. The temporary file is removed on exit.

If interrupted or unsuccessful after starting the outage, the exit handler
attempts restoration and waits for application health. Recovery still
depends on Docker remaining available; SIGKILL and host failure bypass
the handler.

## Application restrictions

The application runs as a non-root user with a read-only root filesystem,
all Linux capabilities dropped and `no-new-privileges` enabled.

```bash
docker inspect "$(docker compose ps -q app)" \
  --format 'User={{.Config.User}} ReadOnly={{.HostConfig.ReadonlyRootfs}} CapDrop={{json .HostConfig.CapDrop}} SecurityOpt={{json .HostConfig.SecurityOpt}}'
```

These restrictions apply to the application service. Nginx has its own
container configuration.

[Application restrictions evidence](../screenshots/AppRestrictions.png)

## Log rotation and correlation

Both services use the `json-file` logging driver with `max-size: 10m`
and `max-file: 3`.

```bash
docker inspect \
  "$(docker compose ps -q app)" \
  "$(docker compose ps -q nginx)" \
  --format '{{.Name}} {{json .HostConfig.LogConfig}}'
```

Rotation limits retained Docker logs; older entries are eventually removed.
It does not provide centralized logging or long-term incident retention.

See the [logging guide](logging.md) for request correlation, upstream timing
fields and the observed log-retrieval limitation.

[Healthchecks and log rotation evidence](../screenshots/HealthChecks_LogRotation.png)

## Retained CI diagnostics

Before cleanup, CI attempts to upload an artifact named
`lab-diagnostics-<run-id>-<attempt>` with seven-day retention.

| File | Contents |
| --- | --- |
| `container-status.txt` | Running and stopped container states |
| `compose.log` | Latest 100 log lines per service |
| `health-status.json` | Service state and recent healthcheck history |

Download it from the workflow run's Summary page. Compare probe failures
with service logs and HTTP errors when investigating an unsuccessful run.

Collection and upload are attempted after test failures. Runner loss,
timeouts or collection errors can prevent complete evidence from being saved.

## Stop the lab

```bash
docker compose down
```

For the original investigation, see
[Incident 001: Backend unavailable](incidents/001-backend-unavailable.md).
