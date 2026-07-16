"""
Inbound agent-facing server (the relay's "receive" side).

Agents (on internal systems) POST their raw scan results here. The collector
authenticates the agent, drops the result into the durable queue, and the
uploader loop forwards it to the platform under the collector's tenant binding.

Endpoints (HTTP, inside the customer network only — never exposed to internet):
  POST /agent/enroll    {name, system_type, enroll_secret}  -> {agent_token}
  POST /agent/results   (Bearer agent_token) {system_type, raw_data, target} -> ok
  GET  /healthz         -> ok

Enrollment uses a shared enroll secret the operator sets on the collector (so a
random process on the network can't register itself as an agent). After
enrollment the agent uses its own token.

Uses only the Python standard library (http.server) to keep the collector
minimal — no extra web framework inside the appliance.
"""
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger("collector.inbound")


def make_handler(registry, result_queue, enroll_secret):
    class Handler(BaseHTTPRequestHandler):
        # quiet default logging; we log meaningfully ourselves
        def log_message(self, *args):
            pass

        def _send(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            length = int(self.headers.get("Content-Length", 0))
            if not length:
                return {}
            try:
                return json.loads(self.rfile.read(length))
            except (ValueError, json.JSONDecodeError):
                return None

        def _bearer(self):
            auth = self.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                return auth[7:]
            return None

        def do_GET(self):
            if self.path == "/healthz":
                self._send(200, {"status": "ok"})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path == "/agent/enroll":
                data = self._body()
                if data is None:
                    return self._send(400, {"error": "invalid json"})
                if data.get("enroll_secret") != enroll_secret:
                    log.warning("Agent enroll rejected: bad enroll secret")
                    return self._send(401, {"error": "invalid enroll secret"})
                name = data.get("name")
                system_type = data.get("system_type")
                if not name or not system_type:
                    return self._send(400, {"error": "name and system_type required"})
                token = registry.enroll(name, system_type)
                log.info("Agent enrolled: %s (%s)", name, system_type)
                return self._send(200, {"agent_token": token,
                                        "note": "Store this token; the agent uses it to submit results."})

            if self.path == "/agent/results":
                token = self._bearer()
                agent = registry.authenticate(token) if token else None
                if not agent:
                    return self._send(401, {"error": "invalid agent token"})
                data = self._body()
                if data is None:
                    return self._send(400, {"error": "invalid json"})
                system_type = data.get("system_type") or agent["system_type"]
                raw = data.get("raw_data")
                if raw is None:
                    return self._send(400, {"error": "raw_data required"})
                result_queue.enqueue(
                    system_type, raw,
                    job_id=data.get("job_id"),
                    target=data.get("target"),
                    framework=data.get("framework"),
                )
                log.info("Received result from agent %s (%s); queued for upload.",
                         agent["name"], system_type)
                return self._send(200, {"status": "ok", "queued": True})

            self._send(404, {"error": "not found"})

    return Handler


def start_inbound_server(registry, result_queue, enroll_secret, host="0.0.0.0", port=8514):
    """Start the agent-facing server in a background thread. Returns the server."""
    handler = make_handler(registry, result_queue, enroll_secret)
    server = ThreadingHTTPServer((host, port), handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    log.info("Inbound agent server listening on %s:%s (internal network only)", host, port)
    return server
