# Investigating HTTP requests with structured logs

Nginx and the Python application write JSON request logs to stdout.
Nginx error logs remain plain text on stderr. Startup and shutdown messages
may also appear alongside JSON entries.

## Read recent logs

Run from the repository root:

```bash
docker compose logs --no-color --no-log-prefix --tail 100 nginx
docker compose logs --no-color --no-log-prefix --tail 100 app
```

Parse only JSON lines when processing this output.

## Correlate a request

```bash
curl --silent --show-error --include --write-out '\n' \
  'http://127.0.0.1:8088/health?source=correlation'
```

Copy the `X-Request-ID` response header. Find the same `request_id` in
the Nginx and application logs.

Nginx generates the ID, forwards it to the application and includes it in
the response. Its `always` header setting also covers error responses.

The application records the forwarded ID in its JSON request log.
Direct application healthchecks bypass Nginx and therefore have a null ID.

A proxy failure before the request reaches the application may have a
Nginx log entry without a matching application entry.

Request IDs correlate records; they are not authentication credentials.

## Nginx fields

| Field | Meaning |
| --- | --- |
| `time` | Request log timestamp, including timezone |
| `request_id` | Identifier returned to the client and forwarded to the application |
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

A value of `0.000` indicates a duration below the displayed resolution.

The application records timestamp, event, request ID, method, URI and status.
Its request log is emitted when response headers are being prepared;
it does not prove that the client received the complete response body.

## Healthy request

A normal health request has client status 200 and upstream status "200".

[Healthy request and JSON access logs](../screenshots/NginxAccessLogs.png)

## Application returns HTTP 404

```bash
curl --silent --show-error --include --write-out '\n' \
  'http://127.0.0.1:8088/does-not-exist?source=logging-guide'
```

In this lab, matching client and upstream statuses of 404 show that the
application returned Not Found. Its application log carries the same
request ID and status.

Restarting containers does not fix an intentionally unknown route.

[Application 404 evidence](../screenshots/404log.png)

## Backend unavailable

Run only against the local lab; this temporarily interrupts the application:

```bash
bash tests/test_recovery.sh
docker compose logs --no-color --no-log-prefix --tail 100 nginx
```

The test stops the backend, expects HTTP 502 or 504, starts it again and
verifies recovery without restarting Nginx.

Inspect the failing access-log entry together with the corresponding
Nginx error message. The error message helps distinguish connection
refusal, connection timeout and timeout while reading the response.

A 504 access-log entry alone does not establish which phase timed out.

[Backend outage log evidence](../screenshots/BEOutage.png)

See the [operations guide](operations.md#test-backend-outage-and-recovery)
for cleanup limitations and manual recovery.

## Automated validation

```bash
python3 tests/test_access_logs.py
```

The four tests verify successful requests, unknown routes, JSON escaping
and distinct request IDs.

They check that response IDs match both proxy and application entries,
including for HTTP 404. They also validate timestamps, statuses and
Nginx timing fields.

Each request carries a unique query marker. The tests poll the latest
100 log entries per service. Heavy concurrent traffic could displace
a matching entry.

The suite runs in GitHub Actions under `Validate JSON access logs`.

[Earlier JSON access-log validation evidence](../screenshots/JSONAcessLogs.png)

## Observed log-retrieval limitation

During local investigation, both Docker and Compose returned the fresh
probe with `--tail 10` and `--tail 100`, but omitted it with `--tail 500`.
A previous time-filtered retrieval also returned no entries.

The underlying cause has not been established. The 100-line window is
a tested workaround for this environment, not a fix to Docker logging.

If a test cannot find an entry, compare retrieval limits and inspect the
raw output before concluding that the application failed to log it.

## Retention and request data

Docker log rotation limits retained logs. Collect relevant evidence before
older entries rotate out.

The `uri` field includes query parameters. Use synthetic request data and
avoid placing credentials or tokens in URLs.

## Find entries by request ID

Copy the 32-character `X-Request-ID` response header into `REQUEST_ID`.
From the repository root, search the latest 100 log lines per service:

    python3 scripts/find_request.py "$REQUEST_ID"

To search a saved CI `compose.log` after the containers have been removed:

    python3 scripts/find_request.py --stdin "$REQUEST_ID" < compose.log

The command prints JSON log lines with an exact `request_id` match. A proxy
failure before the request reaches the app can produce only an Nginx entry.
Exit code `1` means the supplied logs contained no match. Exit code `2` means
the ID was invalid or the live logs could not be read.

## Summarize proxy responses

From the repository root, summarize a saved Compose log:

    python3 scripts/summarize_proxy_logs.py < compose.log

The JSON result counts Nginx responses by HTTP status and groups 5xx
responses by path with query strings removed. Application records and
plain-text Nginx error messages are skipped.

When CI captures `compose.log`, the diagnostics artifact also includes
`proxy-summary.json`. The counts cover only the collected log window and can
include health checks and deliberately failing test requests. Use
`slow-backend.log` for timeout evidence captured before Compose restoration.

### Interpret the latency figures

The GitHub Actions run summary shows timings for all captured proxy requests
and for requests excluding `/health`. The same figures are available in
`proxy-summary.json`. To rebuild the report from a saved `compose.log`, run
this command from the repository root:

    python3 scripts/summarize_proxy_logs.py < compose.log

The `requests` count includes valid access records even when `request_time`
is missing. The `samples` count includes only records with a valid duration.
Both p95 and maximum are reported in seconds.

The p95 is the duration at position `ceil(0.95 × samples)` after sorting the
durations from shortest to longest. With 19 health requests at 10 ms and one
slow request at 5 s, the overall p95 is 10 ms and the maximum is 5 s.
The `excluding_health` group has one timing sample, so its p95 and maximum
are both 5 s. The filter uses the URI path, so `/health?source=smoke` is
also excluded from that group.

Read the sample count alongside the p95. These figures describe the
collected log window, which can include deliberate failures from lab tests.

### Triage proxy latency and errors

From the repository root, render the Markdown shown in GitHub Actions using
an extracted `proxy-summary.json`:

    python3 scripts/render_proxy_summary.py < proxy-summary.json

If you have the raw Compose log, generate the report and render it in one
pipeline:

    python3 scripts/summarize_proxy_logs.py < compose.log |
      python3 scripts/render_proxy_summary.py

Start with the latency section when the symptom is a slow response. Compare
the maximum and p95, then check the timing sample count for the route.
Start with the 5xx section when the symptom is an error. A quick `502` can
rank high by error count while having a low response time. Use the 5xx count
and the total requests for that route to assess how often it failed in the
captured window.

For a specific `504`, follow the request ID into the access log and read
the matching Nginx error record to identify the timeout phase.

## Investigate a slow-backend timeout from CI

Open the relevant GitHub Actions run and download its diagnostics artifact.
Extract it to a directory accessible from the machine where you run the
commands below.

- `slow-backend-summary.json` shows the response status, route, and duration
  recorded by the probe.
- `slow-backend.log` contains the probe output, including the response
  request ID and the Nginx access and error records when captured.

From the repository root, set `log` to the full path of the extracted
`slow-backend.log`. The example assumes you extracted it to
`~/Downloads/lab-diagnostics/`:

    log="$HOME/Downloads/lab-diagnostics/slow-backend.log"
    if [ -r "$log" ]; then
        request_id=$(awk '/^Response:.*X-Request-ID:/ {print $NF; exit}' "$log")
        if [ -n "$request_id" ]; then
            python3 scripts/find_request.py --stdin "$request_id" < "$log"
        else
            printf 'No response request ID found in %s\n' "$log" >&2
        fi
        grep '^Error log:' "$log"
    else
        printf 'Cannot read %s\n' "$log" >&2
    fi

The lookup returns the access record for that exact request ID. Read the
`Error log:` line to identify the phase that timed out. In the slow-backend
scenario, Nginx reports `while reading response header from upstream`.

## Verify request correlation in the running lab

Start the default stack and run the live lookup test:

    docker compose up -d --build --wait --wait-timeout 60
    python3 tests/test_live_request_lookup.py

The test sends one request to `/health`, reads its `X-Request-ID` response
header, and checks that the lookup finds entries from both services. The
same check runs after the stack starts in GitHub Actions.

When investigating a missing match, start with a fresh request. The live
lookup reads only the latest 100 lines per service, and older records can
fall outside that window.
