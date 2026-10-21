#!/usr/bin/env bash
set -euo pipefail
cd /app/GVHMR
exec conda run --no-capture-output -n gvhmr python tools/demo/demo.py "$@"
