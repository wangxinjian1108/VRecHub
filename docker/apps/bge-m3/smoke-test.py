#!/usr/bin/env python3
"""Validate dense, sparse and ColBERT BGE-M3 inference during image build."""
from http.server import ThreadingHTTPServer
import json
import threading
import urllib.request

from bge_m3 import BgeM3Encoder
import server


encoder = BgeM3Encoder()
result = encoder.encode(
    ["A person pushes a suitcase.", "BGE-M3 produces multilingual embeddings."],
    batch_size=2,
    max_length=128,
    return_dense=True,
    return_sparse=True,
    return_colbert_vecs=True,
)
assert result["count"] == 2
assert len(result["dense_vecs"][0]) == 1024
assert all(len(weights) > 0 for weights in result["lexical_weights"])
assert all(len(vectors) > 0 and len(vectors[0]) == 1024 for vectors in result["colbert_vecs"])
print("BGE-M3 dense, sparse and ColBERT inference passed")

server.ENCODER = encoder
httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
thread = threading.Thread(target=httpd.serve_forever, daemon=True)
thread.start()
try:
    base_url = f"http://127.0.0.1:{httpd.server_address[1]}"
    health = json.load(urllib.request.urlopen(base_url + "/health", timeout=5))
    assert health["status"] == "ok"
    request = urllib.request.Request(
        base_url + "/embed",
        data=json.dumps({"text": "HTTP embedding test", "max_length": 64}).encode(),
        headers={"Content-Type": "application/json"},
    )
    response = json.load(urllib.request.urlopen(request, timeout=30))
    assert response["count"] == 1 and len(response["dense_vecs"][0]) == 1024
finally:
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=5)
print("BGE-M3 HTTP service passed")
