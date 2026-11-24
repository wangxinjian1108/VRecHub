# HOI V2 aggregate candidate

This is an unvalidated build definition. It combines the environments for
CHOIS, OMOMO, Kimodo, LIGHT, InterAct, HAIC and GRAIL, plus Blender. The
independent environments remain at their original absolute Conda paths.

The GRAIL, headless InterAct and HAIC stages passed their Actions builds and
are pinned by digest. The InterAct entry-point checks mock creation of
restricted SMPL-H assets; actual inference still requires those assets. Build
only after the corrected LIGHT stage has passed its Actions build and its
immutable image digest has been pinned in the Dockerfile. The manual
workflow requires a large runner and publishes only a candidate tag. GRAIL's
official base is about 89 GB unpacked, before the other environments and
BuildKit's temporary files. Budget at least 200 GB free.

This image definition does not add model weights. GRAIL, LIGHT, InterAct and
HAIC require their respective checkpoints and other external data; CHOIS,
OMOMO and Kimodo likewise need weights and body models to run inference.
Build-time imports alone do not establish that GPU inference or an end-to-end
simulation works. GRAIL and HAIC can also require a newer driver or more GPU
memory than the local L4 host provides.
