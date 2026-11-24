# HAIC runtime build

This stage follows HAIC's Isaac Sim 5.1.0 / Isaac Lab 2.3.2 installation.
The simulator may require a newer NVIDIA driver and supported GPU than the host
used for this repository. HAIC does not ship pretrained policies in its source;
checkpoint files and other external data must be supplied separately. The
stage is intended to be aggregated after its GitHub Actions build and runtime
validation have passed.

Isaac Lab 2.3.2 pins Starlette 0.49.1 for livestreaming, while Isaac Sim
5.1.0 pins FastAPI 0.115.7, which requires Starlette below 0.46. The build
changes Isaac Lab's installation requirement to Starlette 0.45.3 to keep the
simulator's dependency set consistent. Livestreaming has not been validated.
