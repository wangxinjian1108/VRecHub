#!/usr/bin/env bash
set -euo pipefail
cd /app/chois_release
exec conda run --no-capture-output -n hoi python trainer_chois.py \
  --test_sample_res --window=120 --pretrained_model=/models/chois/model-10.pt \
  --input_first_human_pose --use_random_frame_bps --add_language_condition \
  --use_object_keypoints --add_semantic_contact_labels \
  --loss_w_feet=1 --loss_w_fk=0.5 --loss_w_obj_pts=1 \
  --use_guidance_in_denoising "$@"
