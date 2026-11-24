# HAIC runtime build

This stage follows HAIC's Isaac Sim 5.1.0 / Isaac Lab 2.3.2 installation.
The simulator may require a newer NVIDIA driver and supported GPU than the host
used for this repository. HAIC does not ship pretrained policies in its source;
checkpoint files and other external data must be supplied separately. The
stage is intended to be aggregated after its GitHub Actions build and runtime
validation have passed.
