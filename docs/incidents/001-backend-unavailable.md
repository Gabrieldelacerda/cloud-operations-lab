# Incident 001: Backend unavailable

## Scenario

A controlled application outage was introduced by stopping the Python
backend while leaving the Nginx reverse proxy running.

## Impact

Requests to /health through Nginx returned HTTP 504 instead of HTTP 200.

## Reproduction and investigation

```bash
docker compose stop app
curl -i --max-time 5 http://127.0.0.1:8088/health
docker compose ps -a
docker compose logs --tail 20 nginx
```

## Evidence

- The application container was stopped with exit code 137.
- The Nginx container remained running.
- Nginx returned HTTP 504 Gateway Time-out.
- The error log reported:
  `upstream timed out ... while connecting to upstream`.
- Docker inspection reported `OOMKilled=false`.

## Cause

The backend was intentionally stopped. Nginx could not establish a
connection to its upstream application before the connection timeout.

The observed failure occurred during connection establishment, rather
than while waiting for the application to process a request.

## Recovery

```bash
docker compose up -d --wait app
docker compose ps
curl -i --max-time 5 http://127.0.0.1:8088/health
```

The application became healthy and Nginx returned HTTP 200 again.
Recovery did not require restarting Nginx.

## Follow-up

Stopping the application took approximately 10 seconds and produced
exit code 137, consistent with forced termination after the stop timeout.

Explicit SIGTERM handling and shutdown validation remain pending.
