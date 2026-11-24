#!/usr/bin/env bash
set -euo pipefail
export GIT_LFS_SKIP_SMUDGE=1
git config --global url."https://github.com/".insteadOf git@github.com:

checkout() {
    local path="$1" url="$2" revision="$3"
    mkdir -p "$path"
    git -C "$path" init -q
    git -C "$path" remote add origin "$url"
    git -C "$path" -c protocol.version=2 fetch --depth 1 origin "$revision"
    git -C "$path" checkout -q --detach FETCH_HEAD
    test "$(git -C "$path" rev-parse HEAD)" = "$revision"
    git -C "$path" submodule update --init --recursive --depth 1
}

# These are the gitlinks in GRAIL revision 548bbf1219f5ae6d54fe088db841b244ca34e81c.
checkout imports/FoundationPose https://github.com/NVlabs/FoundationPose e3d597b8c6b851d053094ebd6fa240191c5238f8
checkout imports/GEM-X https://github.com/NVlabs/GEM-X.git 20555befe2fbbe5b2015e1fff7ff214dc18ea9d6
checkout imports/Hunyuan3D-2.1 https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1.git 82920d643c0dc2f7bfd7255f45f62d386edfe60c
checkout imports/MoGe https://github.com/microsoft/MoGe.git 74fbce054ebed49800de42d0ad0e83495065719a
checkout imports/MoSE3 https://github.com/mose3-tracker/MoSE3.git 59807f07ff27b5afdf4f35742ac7be88d25e0e3a
checkout imports/Sana https://github.com/NVlabs/Sana.git 5dd502af9938d924be206c332ad1e911b4a925a1
checkout imports/soma-retargeter https://github.com/NVIDIA/soma-retargeter.git cbdb2b494a2af82137bf9b6f15122d60167281c4
