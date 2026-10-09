"""
A stand-in **HTTP API** for the tests of `neuroedge proxy http` (TSK-I2c-15): what a Tasmota or
a home-made REST service looks like to the proxy. Stdlib only.

    python server.py PORT

Every request is appended to the file named by ``UPSTREAM_LOG`` (one JSON line: method, target,
headers, body), so a test can say what the upstream was — and was not — asked.

* ``GET /status``            JSON, with hop-by-hop headers an honest server would send;
* ``POST /cm/<command>``     echoes the command, the query and the body it received;
* ``GET /cm?cmnd=...``       Tasmota style: answers ``{"POWER": "ON"}`` for ``Power On`` (any other command is echoed);
* ``POST /api/<cmd>``        a generic device API: echoes the command and the JSON body it received;
* ``POST /boom``             closes the connection without answering: an upstream that fails;
* anything else              404.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args: object) -> None:  # silence
        return

    def _record(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        path = os.environ.get("UPSTREAM_LOG")
        if path:
            entry = {
                "method": self.command,
                "target": self.path,
                "headers": {k.lower(): v for k, v in self.headers.items()},
                "body": body.decode("utf-8", "replace"),
            }
            with open(path, "a", encoding="utf-8") as log:
                log.write(json.dumps(entry) + "\n")
        return body

    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Keep-Alive", "timeout=5")
        self.send_header("X-Device", "plug-1")
        self.end_headers()
        self.wfile.write(data)

    def _handle(self) -> None:
        body = self._record()
        path, _, query = self.path.partition("?")
        if self.command == "GET" and path == "/status":
            self._send(200, {"power": "ON"})
        elif self.command == "POST" and path.startswith("/cm/"):
            self._send(
                200, {"command": path[4:], "query": query, "body": body.decode()}
            )
        elif self.command == "GET" and path == "/cm":
            from urllib.parse import parse_qs

            command = (parse_qs(query).get("cmnd") or [""])[0]
            self._send(
                200,
                {"POWER": "ON"}
                if command.lower() == "power on"
                else {"command": command},
            )
        elif self.command == "POST" and path.startswith("/api/"):
            self._send(200, {"cmd": path[5:], "body": body.decode()})
        elif self.command == "POST" and path == "/boom":
            self.close_connection = True
            self.connection.close()
        else:
            self._send(404, {"error": "no such thing"})

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _handle


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
