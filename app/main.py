import json
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


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8000), RequestHandler)
    print("Application listening on port 8000", flush=True)
    server.serve_forever()
