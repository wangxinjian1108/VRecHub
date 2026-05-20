---
name: dockerize-submodule
description: Generate or update the Dockerfile and GitHub Actions image workflow for a VRecHub-style submodule. Use when a model already exists under thirdparty and needs a runnable CUDA image and CI publishing pipeline.
---

# Dockerize Submodule

Use this skill when the user asks to dockerize an existing submodule such as `thirdparty/Scal3R` or `Scal3R`.

## Inputs

- A submodule path or submodule name

## Repo assumptions

- Source code is already present as a git submodule under `thirdparty/<name>`
- Docker output path is `docker/<name>/Dockerfile`
- Workflow output path is `.github/workflows/docker-<name>.yml`
- Main image target is `ghcr.io/wangxinjian1108/<name-lowercase>`

## Guardrails

- Read `AGENTS.md` first if it exists
- Reuse nearby Dockerfiles and workflows as the primary style reference
- Build must use local submodule contents from repo root context
- Do not pull project source during `docker build`

## Discovery

1. Resolve the full submodule path from `.gitmodules` if only a short name was provided.
2. Read the submodule README plus any of these that exist:
   - `pyproject.toml`
   - `requirements.txt`
   - `setup.py`
   - `setup.cfg`
   - install scripts
   - `Makefile`
   - docs with install or training instructions
   - any existing CI config
3. Detect:
   - project type
   - Python version
   - CUDA version
   - PyTorch install method
   - required system packages
   - runtime entry point for a smoke test
   - any public or gated model downloads

## Defaults

- If Python is not specified, default to `3.11`
- If CUDA is not specified, use the closest repo convention or default to `12.6`
- Map CUDA to official base images such as:
  - `11.8.0-cudnn8-devel-ubuntu22.04`
  - `12.1.1-cudnn8-devel-ubuntu22.04`
  - `12.6.3-cudnn-devel-ubuntu22.04`
  - `12.8.1-cudnn-devel-ubuntu22.04`

## Dockerfile requirements

Create `docker/<name>/Dockerfile` with this structure:

1. `FROM nvidia/cuda:<resolved-tag>`
2. One `ENV` block containing:
   - `DEBIAN_FRONTEND=noninteractive`
   - `PYTHONDONTWRITEBYTECODE=1`
   - `PYTHONUNBUFFERED=1`
   - `PIP_NO_CACHE_DIR=1`
   - `CONDA_DIR=/opt/conda`
   - `CONDA_ENV=<name>`
3. `WORKDIR /<name>`
4. Install the repo’s standard debug-friendly apt toolchain:
   - `git zsh vim git-lfs wget unzip bzip2 ca-certificates openssh-server clang-format htop iotop rsync ffmpeg curl cmake make less time sqlite3 tree gdb g++ ninja-build build-essential tmux locales lsb-release nano nethogs net-tools valgrind xz-utils sudo pciutils`
5. Add only the extra system packages actually implied by the project dependencies
6. Install Miniconda and create the conda env in one layer
7. Generate SSH host keys
8. Export PATH to the conda env
9. `COPY thirdparty/<name> .`
10. If the target repo depends on sibling submodules, copy those too from the repo root
11. Install project dependencies with `conda run -n "${CONDA_ENV}" ...`
12. If model downloads are documented, download them to `/opt/var/models/<model-name>`
13. Use BuildKit secret `hf_token` for gated Hugging Face downloads
14. Set a minimal `CMD` that performs a real smoke test such as an import or help command

## Workflow requirements

Create `.github/workflows/docker-<name>.yml` with:

- Triggers:
  - push to `master`
  - tags matching `v*.*.*`
  - pull requests to `master`
  - `workflow_dispatch`
- `paths` filters covering:
  - `docker/<name>/**`
  - `thirdparty/<name>`
  - `.github/workflows/docker-<name>.yml`
- One `build-and-push` job on `ubuntu-latest`
- Permissions:
  - `contents: read`
  - `packages: write`
- Steps in this order:
  - checkout with recursive submodules
  - free disk space
  - setup buildx
  - Docker Hub login when not PR and secret exists
  - ghcr login when not PR
  - optional Harbor login if the user explicitly wants Zelos Harbor
  - metadata-action for Docker Hub, ghcr, and optional Harbor
  - build-push-action with `context: .`, `file: docker/<name>/Dockerfile`, and `cache-to/cache-from: type=gha`

## Harbor rule

- If Harbor preference is unknown and the workflow would materially change publishing behavior, ask once
- Default to no Harbor integration unless the user asked for it

## Validation

- Compare with neighboring model Dockerfiles for consistency
- Ensure image naming is lowercase
- Ensure the workflow builds from repo root, not `docker/<name>`
- Ensure all required secrets are referenced correctly

## Done criteria

- `docker/<name>/Dockerfile` exists and matches repo conventions
- `.github/workflows/docker-<name>.yml` exists and is trigger-correct
- The user gets a short report with chosen CUDA base, major dependency decisions, and any unresolved ambiguity
