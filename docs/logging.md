# Investigating HTTP requests with structured logs

Nginx writes one JSON access-log entry per request to stdout.
Error logs remain plain text on stderr. Both are available through Docker Compose.

## Read recent logs

Run from the repository root:

```bash
docker compose logs --no-color --no-log-prefix --tail 50 nginx
```

Startup messages and error logs may appear alongside JSON entries.
Parse only the JSON access-log lines when processing this output.

## Fields

| Field | Meaning |
| --- | --- |
| `time` | Request log timestamp, including timezone |
| `method` | HTTP request method |
| `uri` | Original request URI, including query parameters |
| `status` | HTTP status sent to the client |
| `request_time` | Total request processing time |
| `upstream_addr` | Backend address used for the request |
| `upstream_status` | Status associated with the upstream attempt |
| `upstream_connect_time` | Time establishing the upstream connection |
| `upstream_header_time` | Time receiving the upstream response headers |
| `upstream_response_time` | Time receiving the upstream response |

Durations are expressed in seconds. Timing and upstream fields are JSON
strings because unavailable values and multiple upstream attempts cannot
always be represented as a single number.

A value of `0.000` indicates a duration below the displayed resolution;
it does not mean that no connection or processing occurred.

## Healthy request

```bash
curl --fail --silent --show-error --write-out '\n' \
  'http://127.0.0.1:8088/health?source=logging-guide'
docker compose logs --no-color --no-log-prefix --tail 5 nginx
```

Find the matching URI. A normal health request has client status 200
and upstream status "200".

[Healthy request and JSON access logs](../screenshots/NginxAccessLogs.png)

## Application returns HTTP 404

```bash
curl --silent --show-error --include --write-out '\n' \
  'http://127.0.0.1:8088/does-not-exist?source=logging-guide'
docker compose logs --no-color --no-log-prefix --tail 5 nginx
```

In this lab, matching client and upstream statuses of 404 show that the
request reached the application and the application returned Not Found.
Restarting the containers does not fix an intentionally unknown route.

[Application 404 evidence](../screenshots/404log.png)

## Backend unavailable

The recovery test deliberately stops the application, checks for HTTP
502 or 504, then starts it again and verifies recovery:

```bash
bash tests/test_recovery.sh
docker compose logs --no-color --no-log-prefix --tail 30 nginx
```

Run this only against the local lab: it temporarily interrupts the backend.

Inspect the failing access-log entry together with the corresponding Nginx
error message. The error message helps distinguish a connection refusal,
a connection timeout and a timeout while reading the response.

A 504 access-log entry alone does not establish which phase timed out.
Timing fields provide context; they do not replace the error log.

[Backend outage log evidence](../screenshots/BEOutage.png)

See the [operations guide](operations.md#test-backend-outage-and-recovery)
for cleanup limitations and manual recovery.

## Automated validation

```bash
python3 tests/test_access_logs.py
```

The three tests verify:

- HTTP 200 and 404 requests have matching JSON access-log entries.
- Upstream addresses, statuses, timestamps and timing fields are populated.
- Quotes and backslashes survive JSON encoding and decoding correctly.

Each request carries a unique marker. The tests search the latest 500
entries and briefly poll for log delivery. This is intended for the
low-traffic lab; heavy concurrent traffic could displace a matching entry.

The suite runs in GitHub Actions under `Validate JSON access logs`.

[JSON access-log validation evidence](../screenshots/JSONAcessLogs.png)

## Retention and request data

Docker log rotation limits retained logs. Collect relevant evidence before
older entries rotate out.

The `uri` field includes query parameters. Use synthetic request data in
this lab and avoid placing credentials or tokens in URLs.
