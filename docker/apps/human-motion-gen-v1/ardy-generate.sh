#!/usr/bin/env bash
set -euo pipefail
cd /app/ardy
exec conda run --no-capture-output -n ardy python scripts/generate.py "$@"
