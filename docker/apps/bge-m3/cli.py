#!/usr/bin/env python3
"""CLI for generating BGE-M3 embeddings."""
import argparse
import json
from pathlib import Path
import sys

from bge_m3 import BgeM3Encoder


def read_texts(args):
    texts = list(args.texts)
    if args.input:
        source = sys.stdin if args.input == "-" else Path(args.input).open("r")
        try:
            texts.extend(line.rstrip("\n") for line in source if line.strip())
        finally:
            if source is not sys.stdin:
                source.close()
    if not texts:
        raise SystemExit("Provide text arguments or --input")
    return texts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("texts", nargs="*", help="Texts to encode")
    parser.add_argument("--input", help="UTF-8 text file with one input per line; use - for stdin")
    parser.add_argument("--output", help="Write JSON to this path instead of stdout")
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--max-length", type=int)
    parser.add_argument("--no-dense", action="store_true")
    parser.add_argument("--sparse", action="store_true")
    parser.add_argument("--colbert", action="store_true")
    parser.add_argument("--indent", type=int, default=None)
    args = parser.parse_args()

    result = BgeM3Encoder().encode(
        read_texts(args),
        batch_size=args.batch_size,
        max_length=args.max_length,
        return_dense=not args.no_dense,
        return_sparse=args.sparse,
        return_colbert_vecs=args.colbert,
    )
    payload = json.dumps(result, ensure_ascii=False, indent=args.indent)
    if args.output:
        Path(args.output).write_text(payload + "\n")
    else:
        print(payload)


if __name__ == "__main__":
    main()
