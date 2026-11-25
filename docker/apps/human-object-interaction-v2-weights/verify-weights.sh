#!/usr/bin/env bash
set -euo pipefail
exec /opt/conda/bin/python /opt/hoi-weights-v2/verify.py "$@"
