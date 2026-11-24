# HOI V2 aggregate candidate

This is an unvalidated build definition. It combines the environments for
CHOIS, OMOMO, Kimodo, LIGHT, InterAct, HAIC and GRAIL, plus Blender. The
independent environments remain at their original absolute Conda paths.

The GRAIL, LIGHT, headless InterAct and HAIC stages passed their Actions
builds and are pinned by digest. The LIGHT and InterAct entry-point checks
mock creation of restricted SMPL-H assets; actual inference still requires
those assets. The manual
workflow requires a large runner and publishes only a candidate tag. GRAIL's
official base is about 89 GB unpacked, before the other environments and
BuildKit's temporary files. Budget at least 200 GB free.

This image definition does not add model weights. GRAIL, LIGHT, InterAct and
HAIC require their respective checkpoints and other external data; CHOIS,
OMOMO and Kimodo likewise need weights and body models to run inference.
Build-time imports alone do not establish that GPU inference or an end-to-end
simulation works. GRAIL and HAIC can also require a newer driver or more GPU
memory than the local L4 host provides.

GRAIL's GEM-X environment is installed at `/root/.cache/grail/envs/gem-x`.
Do not mount a host directory over all of `/root/.cache`, since doing so hides
that environment; mount individual model cache directories instead.

LIGHT expects its licensed body models under `/app/LIGHT/models`. InterAct
expects them under `/app/InterAct/models` when invoked from its upstream
`text2interaction` directory. Refer to each upstream README for the required
model layout, checkpoints and datasets. The entry-point checks in this image
only mock body-model creation during the check itself.
