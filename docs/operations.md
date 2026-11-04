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

## Healthchecks

The application healthcheck requests its own `/health` endpoint.

The Nginx healthcheck requests `/health` through the proxy, checking
connectivity to the application as well.

An unhealthy status alone does not trigger a container restart.
The `unless-stopped` policy handles container exits, not healthcheck failures.

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

## Stop the lab

```bash
docker compose down
```

For a documented outage investigation, see
[Incident 001: Backend unavailable](incidents/001-backend-unavailable.md).
