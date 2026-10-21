#!/usr/bin/env bash
set -euo pipefail
cd /app/HY-Motion-1.0
exec conda run --no-capture-output -n hy-motion python local_infer.py "$@"
