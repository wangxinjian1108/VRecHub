# GRAIL runtime (build preparation)

This stage builds on NVIDIA's pinned GRAIL 1.2.0 image and uses the pinned
GRAIL submodule. The workflow is manual because the upstream image is about
89 GB unpacked and its compressed layers occupy another 27.55 GiB. A hosted
runner measured 123 GiB free after cleanup; whether that suffices for the
additional workers is under test. A runner with at least 200 GB free is
recommended.

The build installs the source-bound reconstruction workers and Blender. It
does not download model checkpoints or example datasets. The FlexGEMM GPU
import check is deferred to deployment on a compatible NVIDIA GPU. Upstream
documents a 48 GB RTX 6000 Ada and driver 595.99.02 as its tested setup;
some reconstruction workloads exceed the 24 GB available on the local L4.

This is a build definition, not yet a successfully built or validated image.
GRAIL's external checkpoints, LFS data, system requirements and licenses are
documented at https://github.com/NVlabs/GRAIL.
