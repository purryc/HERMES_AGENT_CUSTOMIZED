from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import unittest
import urllib.error
import urllib.request

from scripts.hermes_tunnel_guard import make_handler, path_allowed


class TunnelGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.upstream_calls: list[dict] = []
        self.upstream_server = ThreadingHTTPServer(("127.0.0.1", 0), self._upstream_handler())
        self.upstream_thread = threading.Thread(target=self.upstream_server.serve_forever, daemon=True)
        self.upstream_thread.start()
        upstream_url = f"http://127.0.0.1:{self.upstream_server.server_address[1]}"

        handler = make_handler(target_url=upstream_url, remote_token="secret-token", timeout_seconds=5)
        self.guard_server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.guard_thread = threading.Thread(target=self.guard_server.serve_forever, daemon=True)
        self.guard_thread.start()
        self.guard_url = f"http://127.0.0.1:{self.guard_server.server_address[1]}"

    def tearDown(self) -> None:
        self.guard_server.shutdown()
        self.guard_server.server_close()
        self.guard_thread.join(timeout=2)
        self.upstream_server.shutdown()
        self.upstream_server.server_close()
        self.upstream_thread.join(timeout=2)

    def test_path_allowlist(self) -> None:
        self.assertTrue(path_allowed("/healthz"))
        self.assertTrue(path_allowed("/api/companion/text-turns"))
        self.assertTrue(path_allowed("/api/jobs/job_123"))
        self.assertFalse(path_allowed("/api/config"))
        self.assertFalse(path_allowed("/api/pty"))

    def test_rejects_missing_token(self) -> None:
        request = urllib.request.Request(f"{self.guard_url}/healthz", method="GET")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(ctx.exception.code, 401)
        self.assertEqual(self.upstream_calls, [])

    def test_rejects_blocked_path(self) -> None:
        request = urllib.request.Request(
            f"{self.guard_url}/api/config",
            headers={"X-Hermes-Remote-Token": "secret-token"},
            method="GET",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(ctx.exception.code, 404)
        self.assertEqual(self.upstream_calls, [])

    def test_forwards_allowed_request_with_token(self) -> None:
        body = json.dumps({"text": "hello"}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.guard_url}/api/companion/text-turns",
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Hermes-Remote-Token": "secret-token",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["path"], "/api/companion/text-turns")
        self.assertEqual(len(self.upstream_calls), 1)
        self.assertEqual(self.upstream_calls[0]["body"], {"text": "hello"})

    def _upstream_handler(self):
        calls = self.upstream_calls

        class Handler(BaseHTTPRequestHandler):
            def do_GET(inner_self) -> None:
                inner_self._reply()

            def do_POST(inner_self) -> None:
                inner_self._reply()

            def _reply(inner_self) -> None:
                length = int(inner_self.headers.get("Content-Length", "0") or "0")
                raw = inner_self.rfile.read(length) if length else b"{}"
                try:
                    body = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    body = {}
                calls.append({"path": inner_self.path, "body": body})
                payload = json.dumps(
                    {
                        "ok": True,
                        "path": inner_self.path.split("?", 1)[0],
                        "body": body,
                    }
                ).encode("utf-8")
                inner_self.send_response(200)
                inner_self.send_header("Content-Type", "application/json")
                inner_self.send_header("Content-Length", str(len(payload)))
                inner_self.end_headers()
                inner_self.wfile.write(payload)

            def log_message(self, format: str, *args) -> None:
                return

        return Handler


if __name__ == "__main__":
    unittest.main()
