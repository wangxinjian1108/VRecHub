#!/usr/bin/env bash
set -euo pipefail
cd /app
exec python3 cli.py "$@"
