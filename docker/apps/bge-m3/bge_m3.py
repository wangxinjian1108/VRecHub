"""Minimal local BGE-M3 encoder used by the CLI and HTTP service."""
import os
import threading

import torch
from FlagEmbedding import BGEM3FlagModel


class BgeM3Encoder:
    def __init__(self):
        self.model_path = os.environ.get("BGE_M3_MODEL_PATH", "/models/bge-m3")
        self.device = os.environ.get("BGE_M3_DEVICE", "cpu")
        self.use_fp16 = os.environ.get("BGE_M3_USE_FP16", "false").lower() in {
            "1",
            "true",
            "yes",
        }
        self.batch_size = int(os.environ.get("BGE_M3_BATCH_SIZE", "8"))
        self.default_max_length = int(os.environ.get("BGE_M3_MAX_LENGTH", "8192"))
        self.max_texts = int(os.environ.get("BGE_M3_MAX_TEXTS", "128"))
        if self.device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError(
                "BGE_M3_DEVICE requests CUDA, but torch.cuda.is_available() is false. "
                "Use the bge-m3-gpu image and run Docker with --gpus all."
            )
        if self.device == "cpu" and self.use_fp16:
            raise RuntimeError("BGE_M3_USE_FP16=true requires a CUDA device")
        torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "4")))
        self._lock = threading.Lock()
        self.model = BGEM3FlagModel(
            self.model_path,
            use_fp16=self.use_fp16,
            devices=self.device,
            batch_size=self.batch_size,
            passage_max_length=self.default_max_length,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )

    def encode(
        self,
        texts,
        batch_size=None,
        max_length=None,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    ):
        if isinstance(texts, str):
            texts = [texts]
        if not isinstance(texts, list) or not texts:
            raise ValueError("texts must be a non-empty string or list of strings")
        if len(texts) > self.max_texts:
            raise ValueError(f"At most {self.max_texts} texts are allowed per request")
        if any(not isinstance(text, str) for text in texts):
            raise ValueError("Every text must be a string")
        if not (return_dense or return_sparse or return_colbert_vecs):
            raise ValueError("At least one embedding type must be requested")

        max_length = int(max_length or self.default_max_length)
        if not 1 <= max_length <= 8192:
            raise ValueError("max_length must be between 1 and 8192")
        batch_size = int(batch_size or self.batch_size)
        if not 1 <= batch_size <= self.max_texts:
            raise ValueError(f"batch_size must be between 1 and {self.max_texts}")

        with self._lock, torch.inference_mode():
            output = self.model.encode(
                texts,
                batch_size=batch_size,
                max_length=max_length,
                return_dense=return_dense,
                return_sparse=return_sparse,
                return_colbert_vecs=return_colbert_vecs,
            )

        result = {
            "model": "BAAI/bge-m3",
            "count": len(texts),
            "dense_dimension": 1024,
        }
        if return_dense:
            result["dense_vecs"] = output["dense_vecs"].astype("float32").tolist()
        if return_sparse:
            result["lexical_weights"] = [
                {token: float(weight) for token, weight in weights.items()}
                for weights in output["lexical_weights"]
            ]
        if return_colbert_vecs:
            result["colbert_vecs"] = [
                vectors.astype("float32").tolist()
                for vectors in output["colbert_vecs"]
            ]
        return result
