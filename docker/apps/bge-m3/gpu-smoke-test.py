#!/usr/bin/env python3
"""Require a physical CUDA device and run all BGE-M3 embedding modes."""
import torch

from bge_m3 import BgeM3Encoder


assert torch.cuda.is_available(), "A physical CUDA device is required"
assert torch.backends.cuda.is_built(), "PyTorch was built without CUDA"
encoder = BgeM3Encoder()
assert encoder.device.startswith("cuda")
assert encoder.use_fp16 is True
result = encoder.encode(
    ["A person pushes a suitcase.", "行人推动一个行李箱。"],
    batch_size=2,
    max_length=128,
    return_dense=True,
    return_sparse=True,
    return_colbert_vecs=True,
)
assert result["count"] == 2
assert len(result["dense_vecs"][0]) == 1024
assert all(weights for weights in result["lexical_weights"])
assert all(vectors and len(vectors[0]) == 1024 for vectors in result["colbert_vecs"])
print(
    "BGE-M3 GPU dense, sparse and ColBERT inference passed:",
    torch.cuda.get_device_name(0),
)
