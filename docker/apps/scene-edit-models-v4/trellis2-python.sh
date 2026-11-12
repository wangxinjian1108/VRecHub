#!/usr/bin/env bash
set -euo pipefail
cd /app/TRELLIS.2
exec conda run --no-capture-output -n trellis2 python "$@"
