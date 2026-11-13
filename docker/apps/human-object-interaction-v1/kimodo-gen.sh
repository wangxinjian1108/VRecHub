#!/usr/bin/env bash
set -euo pipefail
cd /app/kimodo
exec conda run --no-capture-output -n kimodo kimodo_gen "$@"
