#!/usr/bin/env bash
set -euo pipefail
cd /app/chois_release
exec conda run --no-capture-output -n hoi python trainer_chois.py --test_sample_res "$@"
