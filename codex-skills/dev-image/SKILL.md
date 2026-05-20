---
name: dev-image
description: Generate a Kubernetes Notebook development image for a VRecHub model from its runtime/base image. Use after add-repo or dockerize-submodule when the user needs an sshd plus JupyterLab dev image with NB_PREFIX support.
---

# Dev Image

Use this skill when the user wants a dev image derived from the runtime image produced by `add-repo` or `dockerize-submodule`.

## Inputs

- A model name or submodule path such as `vggt` or `thirdparty/vggt`
- Optional base image override

## Repo assumptions

- Runtime Dockerfile is `docker/<name>/Dockerfile`
- Runtime image is `ghcr.io/wangxinjian1108/<name>:latest`
- Dev Dockerfile should be `docker/<name>/Dockerfile.dev`
- Dev image build should be appended to `.github/workflows/docker-<name>.yml`
- Dev image should be `ghcr.io/wangxinjian1108/<name>:dev`
- `docker/Dockerfile.dev` is the reference template

## Dev image requirements

The generated dev image must:

- use the runtime image as `BASE_IMAGE`
- install s6-overlay
- start both `sshd` and `jupyter lab` through s6 services
- support `NB_PREFIX` as an environment variable for Kubernetes Notebook routing
- create a `jovyan` user and run JupyterLab as `jovyan`
- give `jovyan` passwordless sudo so it can operate with root-equivalent permissions
- create `${HOME}/.ssh/id_rsa` for `jovyan`
- add `${HOME}/.ssh/id_rsa.pub` to `${HOME}/.ssh/authorized_keys`
- check whether `root` has a password and set `root:ShARC` only when missing or locked
- enable SSH password and public key authentication
- expose SSH and Jupyter ports

## Runtime user note

s6 must start as root to launch `sshd` correctly on port 22 and to switch JupyterLab to `jovyan`. Treat `jovyan` as the default notebook user. Do not set Docker `USER jovyan` unless also changing the SSH design to a non-root-compatible variant.

## Dockerfile workflow

1. Resolve `<name>` from `.gitmodules` if a submodule path was not provided.
2. Verify `docker/<name>/Dockerfile` exists.
3. Copy the structure of `docker/Dockerfile.dev` into `docker/<name>/Dockerfile.dev`.
4. Set the default base image:
   ```dockerfile
   ARG BASE_IMAGE=ghcr.io/wangxinjian1108/<name>:latest
   FROM ${BASE_IMAGE}
   ```
5. Keep the base configurable with `--build-arg BASE_IMAGE=...`.
6. Preserve these env vars:
   - `NB_USER=jovyan`
   - `NB_UID=1000`
   - `NB_GID=100`
   - `HOME=/home/jovyan`
   - `JUPYTER_PORT=8888`
   - `SSH_PORT=22`
   - `NB_PREFIX=/`
7. In the Jupyter s6 run script, pass:
   ```bash
   --ServerApp.base_url="${NB_PREFIX:-/}"
   ```
8. Install JupyterLab with `python -m pip` so the runtime image's active Python or conda env is used.

## Workflow integration

Extend `.github/workflows/docker-<name>.yml`; do not create a separate dev workflow.

The single workflow should still have:

- push to `master`
- tags matching `v*.*.*`
- pull requests to `master`
- `workflow_dispatch`
- paths for:
  - `docker/<name>/**`
  - `thirdparty/<name>`
  - `.github/workflows/docker-<name>.yml`

The workflow must:

- build the runtime image first from `docker/<name>/Dockerfile` with `load: true`
- tag that runtime image with a local temporary tag such as `<name>:runtime-<shortsha>`
- for push/tag builds, push the runtime tags after the runtime image has loaded locally
- publish runtime as `ghcr.io/${{ github.repository_owner }}/<name>:latest` on the default branch
- always publish a runtime `sha-<shortsha>` tag, and add that exact tag explicitly to the runtime build-push `tags` list
- build the dev image from `docker/<name>/Dockerfile.dev` with `BASE_IMAGE=<name>:runtime-<shortsha>`
- publish GHCR as `ghcr.io/${{ github.repository_owner }}/<name>:dev`
- publish Docker Hub as `${{ secrets.DOCKERHUB_USERNAME }}/<name>:dev` only if `DOCKERHUB_USERNAME` exists
- also push a `dev-sha-<shortsha>` tag for traceability
- never push `latest` from the dev workflow; `latest` belongs to the runtime workflow
- use GHA cache for the runtime build
- on pull requests, build runtime to the same local temporary tag and build dev from that local tag; do not push either image

## Validation

- Ensure the generated Dockerfile does not copy secrets such as `config/token.yaml`
- Ensure private keys are generated inside the image only because the user explicitly requested it
- Build locally if Docker is available:
  ```bash
  docker build -f docker/<name>/Dockerfile.dev --build-arg BASE_IMAGE=ghcr.io/wangxinjian1108/<name>:latest -t <name>:dev-test .
  ```
- Smoke test if Docker is available:
  ```bash
  docker run --rm -e NB_PREFIX=/notebook/<name>/ -p 8888:8888 -p 2222:22 <name>:dev-test
  ```

## Done criteria

- `docker/<name>/Dockerfile.dev` exists
- `.github/workflows/docker-<name>.yml` builds both runtime and dev images
- The dev image derives from the runtime image
- JupyterLab uses `NB_PREFIX`
- `sshd` and JupyterLab are both managed by s6
- The workflow builds runtime first, then builds dev from the same runtime sha tag
- The report includes the dev image name and any security caveat about baked SSH keys
