from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Iterable


ALLOWED_PREFIXES = (
    "/healthz",
    "/api/companion/text-turns",
    "/api/companion/voice-turns",
    "/api/companion/audio",
    "/api/jobs",
    "/api/skills",
)
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


def path_allowed(path: str, prefixes: Iterable[str] = ALLOWED_PREFIXES) -> bool:
    normalized = "/" + path.lstrip("/")
    return any(normalized == prefix or normalized.startswith(f"{prefix}/") for prefix in prefixes)


def make_handler(target_url: str, remote_token: str, timeout_seconds: int):
    target = target_url.rstrip("/")

    class TunnelGuardHandler(BaseHTTPRequestHandler):
        server_version = "HermesTunnelGuard/1.0"

        def do_GET(self) -> None:
            self._proxy()

        def do_POST(self) -> None:
            self._proxy()

        def do_PUT(self) -> None:
            self._proxy()

        def do_DELETE(self) -> None:
            self._proxy()

        def do_OPTIONS(self) -> None:
            self._send_json(204, {})

        def _proxy(self) -> None:
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return

            parsed = urllib.parse.urlsplit(self.path)
            if not path_allowed(parsed.path):
                self._send_json(404, {"error": "path_not_allowed", "path": parsed.path})
                return

            body = self._read_body()
            url = urllib.parse.urlunsplit(
                urllib.parse.urlsplit(f"{target}{parsed.path}?{parsed.query}" if parsed.query else f"{target}{parsed.path}")
            )
            headers = self._forward_headers()
            request = urllib.request.Request(
                url,
                data=body if self.command not in {"GET", "HEAD"} else None,
                headers=headers,
                method=self.command,
            )
            try:
                with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                    self._send_upstream_response(response.status, response.headers, response.read())
            except urllib.error.HTTPError as exc:
                self._send_upstream_response(exc.code, exc.headers, exc.read())
            except urllib.error.URLError as exc:
                self._send_json(502, {"error": "upstream_unreachable", "detail": str(exc.reason)})

        def _authorized(self) -> bool:
            provided = self.headers.get("X-Hermes-Remote-Token", "")
            return bool(remote_token) and provided == remote_token

        def _read_body(self) -> bytes:
            length = int(self.headers.get("Content-Length", "0") or "0")
            return self.rfile.read(length) if length else b""

        def _forward_headers(self) -> dict[str, str]:
            headers: dict[str, str] = {}
            for key, value in self.headers.items():
                lowered = key.lower()
                if lowered in HOP_BY_HOP_HEADERS:
                    continue
                if lowered in {"host", "content-length", "x-hermes-remote-token"}:
                    continue
                headers[key] = value
            return headers

        def _send_upstream_response(self, status: int, headers, body: bytes) -> None:
            self.send_response(status)
            for key, value in headers.items():
                if key.lower() in HOP_BY_HOP_HEADERS or key.lower() == "content-length":
                    continue
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if status != 204:
                self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            sys.stderr.write("hermes-tunnel-guard: " + (format % args) + "\n")

    return TunnelGuardHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Protected local proxy for Hermes Cloudflare tunnel.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--target", default="http://127.0.0.1:8787")
    parser.add_argument("--token", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=45)
    args = parser.parse_args()

    if not args.token.strip():
        raise SystemExit("--token is required")

    handler = make_handler(
        target_url=args.target,
        remote_token=args.token.strip(),
        timeout_seconds=args.timeout_seconds,
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Hermes tunnel guard listening on http://{args.host}:{args.port} -> {args.target}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
