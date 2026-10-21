#!/usr/bin/env bash
set -euo pipefail
cd /app/Motion2MixamoRig
exec conda run --no-capture-output -n m2mr m2mr "$@"
