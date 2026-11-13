#!/usr/bin/env bash
set -euo pipefail
cd /app/omomo_release
exec conda run --no-capture-output -n hoi python trainer_hand_foot_manip_diffusion.py --run_whole_pipeline "$@"
