# Incident 002: Slow backend response

The lab reproduced HTTP 504 on `/lab/slow` while the backend was running.
Nginx connected to the application but timed out waiting for response headers.

## Reproduce

From the repository root, run:

```bash
bash tests/test_slow_backend.sh
```

The script verifies that `/lab/slow` returns 404 with the default
configuration. It then applies `compose.slow.yaml`, runs the probe and
checks `/health`. On exit, it attempts to restore the default configuration
and verifies that `/lab/slow` returns 404 again.

## Evidence

In the initial local run, the client received HTTP 504 with request ID
`979a7b8966af7f82b0413378159bd293`. The matching Nginx access log showed:

| Field | Observed value |
| --- | --- |
| Client status | `504` |
| Total request time | `5.005 s` |
| Upstream connection time | `0.001 s` |
| Upstream header time | `-` |

The probe matched the access log to the response using `X-Request-ID`.
It matched the error log using the unique query marker in the URI.
The error log reported `while reading response header from upstream`.

A subsequent `/health` request returned HTTP 200 while the slow route
was still enabled.

## Diagnosis

The Compose override enables a route that waits eight seconds before
sending response headers. The proxy gives up after about five seconds
while waiting for those headers.

The HTTP status is shared by both exercises. The error-log phase identifies
where each request stalled.

| Scenario | Observed Nginx error phase |
| --- | --- |
| Backend stopped | `while connecting to upstream` |
| Backend slow | `while reading response header from upstream` |

See [Incident 001: Backend unavailable](001-backend-unavailable.md) for
the stopped-backend evidence.

## Restore the default configuration

If the automated restoration fails, apply the base configuration:

```bash
docker compose -f compose.yaml up -d --wait --wait-timeout 60
python3 tests/http_smoke.py
curl -sS -o /dev/null -w 'Slow route: HTTP %{http_code}\n' \
  --max-time 10 http://127.0.0.1:8088/lab/slow
```

Expect the smoke tests to pass and the slow route to return 404.
