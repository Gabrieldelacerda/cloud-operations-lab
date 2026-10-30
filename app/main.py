import json
import signal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path

        if path == "/":
            status = 200
            payload = {"service": "cloud-operations-lab", "message": "Application running"}
        elif path == "/health":
            status = 200
            payload = {"status": "ok"}
        else:
            status = 404
            payload = {"error": "Not found"}

        body = json.dumps(payload).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    stopping = False

    def request_shutdown(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)

    with ThreadingHTTPServer(("0.0.0.0", 8000), RequestHandler) as server:
        server.timeout = 0.5
        print("Application listening on port 8000", flush=True)

        while not stopping:
            server.handle_request()

    print("Application stopped cleanly", flush=True)


if __name__ == "__main__":
    main()
