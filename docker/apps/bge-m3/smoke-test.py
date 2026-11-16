#!/usr/bin/env python3
"""Validate dense, sparse and ColBERT BGE-M3 inference during image build."""
from bge_m3 import BgeM3Encoder


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
