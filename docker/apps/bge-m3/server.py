#!/usr/bin/env python3
"""Small dependency-free HTTP service for BGE-M3 embeddings."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os

from bge_m3 import BgeM3Encoder


ENCODER = None


class Handler(BaseHTTPRequestHandler):
    server_version = "BGEM3Server/1.0"

    def _send(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(
                200,
                {
                    "status": "ok",
                    "model": "BAAI/bge-m3",
                    "device": ENCODER.device,
                    "fp16": ENCODER.use_fp16,
                },
            )
        elif self.path == "/info":
            self._send(
                200,
                {
                    "model": "BAAI/bge-m3",
                    "device": ENCODER.device,
                    "fp16": ENCODER.use_fp16,
                    "dense_dimension": 1024,
                    "default_max_length": ENCODER.default_max_length,
                    "default_batch_size": ENCODER.batch_size,
                },
            )
        elif self.path == "/":
            self._send(
                200,
                {
                    "service": "BGE-M3 embedding server",
                    "endpoints": ["GET /health", "GET /info", "POST /embed"],
                },
            )
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/embed":
            self._send(404, {"error": "not found"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if not 0 < content_length <= 16 * 1024 * 1024:
                raise ValueError("request body must be between 1 byte and 16 MiB")
            request = json.loads(self.rfile.read(content_length))
            texts = request.get("texts")
            if texts is None and "text" in request:
                texts = [request["text"]]
            result = ENCODER.encode(
                texts,
                batch_size=request.get("batch_size"),
                max_length=request.get("max_length"),
                return_dense=request.get("return_dense", True),
                return_sparse=request.get("return_sparse", False),
                return_colbert_vecs=request.get("return_colbert_vecs", False),
            )
            self._send(200, result)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._send(400, {"error": str(error)})
        except Exception as error:
            self.log_error("embedding failed: %s", error)
            self._send(500, {"error": "embedding failed", "type": type(error).__name__})

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}", flush=True)


def main():
    global ENCODER
    ENCODER = BgeM3Encoder()
    host = os.environ.get("BGE_M3_HOST", "0.0.0.0")
    port = int(os.environ.get("BGE_M3_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(
        f"BGE-M3 server listening on http://{host}:{port} "
        f"(device={ENCODER.device}, fp16={ENCODER.use_fp16})",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
