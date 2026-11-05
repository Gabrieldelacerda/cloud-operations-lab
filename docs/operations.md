# Operating the lab

## Start and validate

Run commands from the repository root:

```bash
docker compose up -d --build --wait --wait-timeout 60
python3 tests/http_smoke.py
```

Both services should report healthy:

```bash
docker compose ps
```

## Collect diagnostics

```bash
bash scripts/diagnose.sh
```

The script validates Compose configuration, lists running and stopped
containers, prints recent logs and requests the health endpoint through Nginx.

It exits with a nonzero status if any command fails, including an HTTP error
from the health endpoint. It does not restart or modify containers.

[Diagnostics running in CI](../screenshots/Environment_Diagnostics_CI.png)

## Healthchecks

The application healthcheck requests its own `/health` endpoint.

The Nginx healthcheck requests `/health` through the proxy, checking
connectivity to the application as well.

An unhealthy status alone does not trigger a container restart.
The `unless-stopped` policy handles container exits, not healthcheck failures.

## Test backend outage and recovery

This test temporarily interrupts the application in the current Compose
project. Run it only against the local lab:

```bash
bash tests/test_recovery.sh
```

The test:

1. Confirms both containers are running and the HTTP smoke tests pass.
2. Stops the application and expects HTTP 502 or 504 through Nginx.
3. Starts the same application container and polls for HTTP 200.
4. Reruns the four HTTP smoke tests.
5. Checks that Nginx is still running with the same container ID and start time.

The observed local run returned HTTP 504 during the outage and passed all
HTTP checks after recovery without restarting Nginx.

[Backend outage and recovery evidence](../screenshots/testrecovery.png)

The script explicitly restores the backend; this is not automatic failover.
If the test fails or receives SIGINT or SIGTERM, its exit handler attempts
to start the application again. That cleanup attempt does not verify
application health and cannot run after SIGKILL or host failure.

If restoration fails, recover manually and validate:

```bash
docker compose up -d --wait --wait-timeout 60 app
python3 tests/http_smoke.py
```

## Application restrictions

The application runs as a non-root user with:

- A read-only root filesystem.
- All Linux capabilities dropped.
- Privilege escalation through exec disabled with `no-new-privileges`.

Inspect the applied configuration:

```bash
docker inspect "$(docker compose ps -q app)" \
  --format 'User={{.Config.User}} ReadOnly={{.HostConfig.ReadonlyRootfs}} CapDrop={{json .HostConfig.CapDrop}} SecurityOpt={{json .HostConfig.SecurityOpt}}'
```

These restrictions apply to the application service. Nginx has its own
container configuration.

[Application restrictions evidence](../screenshots/AppRestrictions.png)

## Log rotation

Both services use the `json-file` logging driver with:

- `max-size: 10m`
- `max-file: 3`

Inspect the applied settings:

```bash
docker inspect \
  "$(docker compose ps -q app)" \
  "$(docker compose ps -q nginx)" \
  --format '{{.Name}} {{json .HostConfig.LogConfig}}'
```

Rotation limits retained Docker logs; older entries are eventually removed.
It does not provide centralized logging or long-term incident retention.

[Healthchecks and log rotation evidence](../screenshots/HealthChecks_LogRotation.png)

## Stop the lab

```bash
docker compose down
```

For a documented outage investigation, see
[Incident 001: Backend unavailable](incidents/001-backend-unavailable.md).
