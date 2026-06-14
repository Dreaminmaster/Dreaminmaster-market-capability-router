from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .candidate import CandidateEvaluator
from .engine import MarketCapabilityRouter


class MCRRequestHandler(BaseHTTPRequestHandler):
    engine = MarketCapabilityRouter()
    evaluator = CandidateEvaluator()

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"status": "ok", "service": "market-capability-router", "version": "0.2.0"})
            return
        self._send(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
        except Exception as exc:
            self._send(400, {"error": "invalid_json", "detail": str(exc)})
            return

        if self.path == "/analyze":
            text = payload.get("text")
            if not isinstance(text, str) or not text.strip():
                self._send(400, {"error": "text_required"})
                return
            self._send(200, self.engine.analyze(text).to_dict())
            return

        if self.path == "/candidate/evaluate":
            candidate = payload.get("candidate")
            need_terms = payload.get("need_terms", [])
            if not isinstance(candidate, dict):
                self._send(400, {"error": "candidate_object_required"})
                return
            if not isinstance(need_terms, list):
                self._send(400, {"error": "need_terms_must_be_list"})
                return
            result = self.evaluator.evaluate(candidate, [str(x) for x in need_terms])
            data = result.__dict__.copy()
            data["risk_flags"] = [flag.__dict__ for flag in result.risk_flags]
            self._send(200, data)
            return

        self._send(404, {"error": "not_found"})

    def log_message(self, format: str, *args: Any) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), MCRRequestHandler)
    print(f"MCR API listening on http://{host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
