"""Demo API server (plan Phase 8). Run from the repo root:

    .venv/bin/python -m api.app            # http://127.0.0.1:8000

Endpoints are described in docs/api-contract.md. The server binds to
localhost only and keeps rendered previews in a private temporary folder.
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from api.render_adapter import render_preview, renderer_available
from api.schemas import MAX_BODY_BYTES, RequestError, validate_request
from engine.decision_policy import suggest_policies
from engine.layouts import generate_candidates
from engine.ranking import rank_candidates
from engine.resize import resize

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
PREVIEW_PATH = re.compile(r"^/api/previews/([0-9a-f]{32})\.png$")


def resize_with_debug(source: dict, target_canvas: dict) -> tuple[dict, dict[str, Any] | None]:
    """The same pipeline as ``resize()``, keeping the ranker's diagnostics.

    If the diagnostics cannot be built, or no candidate is legal, the design
    comes from ``resize()`` itself and debug is None, as the contract allows.
    """
    try:
        policies = suggest_policies(source, target_canvas)
        candidates = generate_candidates(source, target_canvas, policies)
        best, diagnostics = rank_candidates(source, target_canvas, candidates, policies)
    except Exception:  # noqa: BLE001 - debug data is optional by contract
        return resize(source, target_canvas), None
    if best is None:
        return resize(source, target_canvas), diagnostics
    return best, diagnostics


def make_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    preview_dir = Path(tempfile.mkdtemp(prefix="chameleon-previews-"))

    class Handler(BaseHTTPRequestHandler):
        server_version = "ChameleonDemo/1"

        def do_GET(self) -> None:  # noqa: N802 - http.server naming
            if self.path == "/api/health":
                self._json(HTTPStatus.OK, {"status": "ok", "renderer": renderer_available()})
                return
            match = PREVIEW_PATH.match(self.path)
            if match:
                png = preview_dir / f"{match.group(1)}.png"
                if png.is_file():
                    self._send(HTTPStatus.OK, png.read_bytes(), "image/png")
                    return
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802 - http.server naming
            if self.path != "/api/resize":
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if not 0 < length <= MAX_BODY_BYTES:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "body must be 1 byte to 2 MB of JSON"})
                return
            try:
                body = json.loads(self.rfile.read(length))
                source, target_canvas = validate_request(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._json(HTTPStatus.BAD_REQUEST, {"error": "body is not valid JSON"})
                return
            except RequestError as error:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
                return

            design, debug = resize_with_debug(source, target_canvas)
            preview_url = None
            preview_id = uuid.uuid4().hex
            try:
                warnings = render_preview(design, preview_dir / f"{preview_id}.png")
                preview_url = f"/api/previews/{preview_id}.png"
            except Exception as error:  # noqa: BLE001 - a preview failure must not hide the design
                warnings = [f"preview failed: {type(error).__name__}"]
            if debug is not None:
                debug["warnings"] = list(debug.get("warnings", [])) + warnings
            self._json(
                HTTPStatus.OK, {"design": design, "preview_url": preview_url, "debug": debug}
            )

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
            pass

        def _json(self, status: HTTPStatus, payload: Any) -> None:
            self._send(status, json.dumps(payload).encode("utf-8"), "application/json")

        def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Chameleon demo API (development only)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    server = make_server(DEFAULT_HOST, args.port)
    print(f"Chameleon demo API on http://{DEFAULT_HOST}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
