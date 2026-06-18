# vrec-models-v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single Docker image `ghcr.io/wangxinjian1108/vrec-models-v1` that bundles inference code + per-model conda env for FoundationStereo, Pi3, vggt-omega, sam3 (and sam3.1 weights), with a paired `:dev` image (SSH + JupyterLab).

**Architecture:** One CUDA 12.8 devel base, four isolated conda envs under `/opt/conda/envs/{foundation_stereo,pi3,vggt-omega,sam3}`, source code mounted at `/app/<name>`. Weights NOT baked — mounted at `/opt/var/models/` at runtime. Dev image extends runtime via standard s6-overlay + SSH + JupyterLab template.

**Tech Stack:** Docker (buildx, BuildKit), GitHub Actions, Miniconda, PyTorch (cu124/cu126/cu128 mixed via wheel index), s6-overlay v3.2.0.2.

## Global Constraints

- Base image: `nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04`
- Repo path: `docker/apps/vrec-models-v1/`
- Image name: `ghcr.io/wangxinjian1108/vrec-models-v1` + Docker Hub mirror via `${{ secrets.DOCKERHUB_USERNAME }}/vrec-models-v1`
- Runtime tags: `latest`, `sha-<7>`, `<branch>`, `v*.*.*`. Dev tags: `dev`, `dev-sha-<7>`
- Source layout in image: `/app/{foundation_stereo,pi3,vggt-omega,sam3}`
- conda env names: `foundation_stereo`, `pi3`, `vggt-omega`, `sam3`
- env Python: 3.11 / 3.10 / 3.10 / 3.12
- env PyTorch: 2.4.1 cu124 / 2.5.1 cu124 / 2.6.0 cu126 / 2.10.0 cu128
- Runtime CMD: `["/bin/bash"]` (no auto-activated env in PATH)
- Dev image: s6-overlay v3.2.0.2 + SSH(:22) + JupyterLab(:8888) + jovyan UID=1000/GID=100 + root password `ShARC`
- Workflow path filter triggers on `docker/apps/vrec-models-v1/**` + the four submodule dirs + workflow file
- Skill `dockerize-submodule.md` apt list permanently gains `libarchive-tools` and `netcat-openbsd`
- Weights are NOT baked into the image — `/opt/var/models/` is an empty dir, mounted at runtime

## File Structure

**Created:**
- `docker/apps/vrec-models-v1/Dockerfile` — runtime image
- `docker/apps/vrec-models-v1/Dockerfile.dev` — dev layer (FROM runtime)
- `.github/workflows/docker-vrec-models-v1.yml` — CI: build + push runtime + dev to GHCR (and Docker Hub if secret set)

**Modified:**
- `.claude/commands/dockerize-submodule.md` — add `libarchive-tools` and `netcat-openbsd` to fixed apt list

---

### Task 1: Skill template — add libarchive-tools + netcat-openbsd

**Files:**
- Modify: `.claude/commands/dockerize-submodule.md` (apt block in step 3.c, between lines 37–73)

**Interfaces:**
- Consumes: nothing
- Produces: updated skill template that future `/add-repo` invocations will use

This is a docs-only change to a markdown skill template. No tests run; verification is `grep`.

- [ ] **Step 1: Read current apt block**

Run: `grep -n "pciutils" .claude/commands/dockerize-submodule.md`
Expected: matches the line with `pciutils \` inside the fixed apt list (around line 72).

- [ ] **Step 2: Add the two packages**

Edit `.claude/commands/dockerize-submodule.md` — within the apt list, after `pciutils \` and before `&& rm -rf /var/lib/apt/lists/*`, insert:

```
        libarchive-tools \
        netcat-openbsd \
```

So the trailing portion of the list reads:

```
        sudo \
        pciutils \
        libarchive-tools \
        netcat-openbsd \
        && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 3: Verify with grep**

Run: `grep -n "libarchive-tools\|netcat-openbsd" .claude/commands/dockerize-submodule.md`
Expected: two matches, both inside the apt block.

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/dockerize-submodule.md
git commit -m "chore: add libarchive-tools + netcat-openbsd to dockerize-submodule apt template"
```

---

### Task 2: Runtime Dockerfile — base + apt + locale + miniconda + ssh-keygen

**Files:**
- Create: `docker/apps/vrec-models-v1/Dockerfile`

**Interfaces:**
- Consumes: nothing
- Produces: a partial Dockerfile through the miniconda + ssh-keygen layer; later tasks append to it. After this task the image won't yet have any conda env or model code.

This task lays down everything except the conda envs and the per-model COPY/install layers, so cache resets in later tasks don't redo apt and miniconda.

- [ ] **Step 1: Create the Dockerfile (base through ssh-keygen)**

Create `docker/apps/vrec-models-v1/Dockerfile` with this content:

```dockerfile
FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONDA_DIR=/opt/conda

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    zsh \
    vim \
    git-lfs \
    wget \
    unzip \
    bzip2 \
    ca-certificates \
    openssh-server \
    clang-format \
    htop \
    iotop \
    rsync \
    ffmpeg \
    curl \
    cmake \
    make \
    less \
    time \
    sqlite3 \
    tree \
    gdb \
    g++ \
    ninja-build \
    build-essential \
    tmux \
    locales \
    lsb-release \
    nano \
    nethogs \
    net-tools \
    valgrind \
    xz-utils \
    sudo \
    pciutils \
    libarchive-tools \
    netcat-openbsd \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libturbojpeg0-dev \
    && rm -rf /var/lib/apt/lists/*

RUN locale-gen en_US.UTF-8 zh_CN.UTF-8 \
    && update-locale LANG=en_US.UTF-8

ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p "${CONDA_DIR}" \
    && rm -f /tmp/miniconda.sh \
    && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/main \
    && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/r \
    && "${CONDA_DIR}/bin/conda" init bash \
    && "${CONDA_DIR}/bin/conda" clean -afy

RUN mkdir -p /var/run/sshd /root/.ssh \
    && ssh-keygen -A

ENV PATH=${CONDA_DIR}/bin:${PATH}

# placeholder: per-model env + code follows in later tasks
```

- [ ] **Step 2: Verify the file is well-formed**

Run: `docker build --target=- -f docker/apps/vrec-models-v1/Dockerfile docker/apps/vrec-models-v1/ 2>&1 | head -5 || true`

This will fail (we're not building yet, no `--target`), but we just want syntax sanity. Instead use:

Run: `head -5 docker/apps/vrec-models-v1/Dockerfile`
Expected: prints `FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04` and the ENV block.

- [ ] **Step 3: Commit**

```bash
git add docker/apps/vrec-models-v1/Dockerfile
git commit -m "feat(vrec-models-v1): scaffold runtime Dockerfile (base + apt + miniconda)"
```

---

### Task 3: Runtime Dockerfile — create the four conda envs

**Files:**
- Modify: `docker/apps/vrec-models-v1/Dockerfile` (append after the placeholder comment)

**Interfaces:**
- Consumes: `${CONDA_DIR}` and `conda` from Task 2
- Produces: `/opt/conda/envs/{foundation_stereo,pi3,vggt-omega,sam3}` — empty Python envs that Tasks 4–7 install into.

Single RUN that creates all four envs and cleans cache. Later per-model tasks each consume one of these envs.

- [ ] **Step 1: Append the env-creation layer**

Replace the `# placeholder: per-model env + code follows in later tasks` line in `docker/apps/vrec-models-v1/Dockerfile` with:

```dockerfile
RUN conda create -n foundation_stereo python=3.11 -y \
 && conda create -n pi3                python=3.10 -y \
 && conda create -n vggt-omega         python=3.10 -y \
 && conda create -n sam3               python=3.12 -y \
 && conda clean -afy

# placeholder: per-model COPY + pip installs follow in later tasks
```

- [ ] **Step 2: Verify**

Run: `grep -c "conda create -n" docker/apps/vrec-models-v1/Dockerfile`
Expected: `4`

- [ ] **Step 3: Commit**

```bash
git add docker/apps/vrec-models-v1/Dockerfile
git commit -m "feat(vrec-models-v1): create four conda envs (foundation_stereo/pi3/vggt-omega/sam3)"
```

---

### Task 4: Runtime Dockerfile — install foundation_stereo

**Files:**
- Modify: `docker/apps/vrec-models-v1/Dockerfile`

**Interfaces:**
- Consumes: env `foundation_stereo` from Task 3, `thirdparty/FoundationStereo/` from build context
- Produces: `/app/foundation_stereo` populated, env has torch 2.4.1 cu124 + deps + flash-attn + xformers

Mirrors the install steps from `docker/FoundationStereo/Dockerfile` (lines 64–77), inside `conda run -n foundation_stereo`.

- [ ] **Step 1: Append foundation_stereo layer**

Replace the `# placeholder: per-model COPY + pip installs follow in later tasks` line with:

```dockerfile
COPY thirdparty/FoundationStereo /app/foundation_stereo

RUN conda run -n foundation_stereo pip install --no-cache-dir \
        torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 \
        --index-url https://download.pytorch.org/whl/cu124 \
 && conda run -n foundation_stereo pip install --no-cache-dir \
        scikit-image omegaconf opencv-contrib-python imgaug ninja timm \
        albumentations scipy joblib scikit-learn ruamel.yaml trimesh \
        pyyaml imageio open3d transformations einops gdown \
        huggingface-hub xformers==0.0.28.post1 \
 && conda run -n foundation_stereo pip install --no-cache-dir \
        flash-attn --no-build-isolation

# placeholder: pi3 follows
```

- [ ] **Step 2: Verify**

Run: `grep -n "foundation_stereo" docker/apps/vrec-models-v1/Dockerfile | head`
Expected: env-creation line + COPY + 3 install lines.

- [ ] **Step 3: Commit**

```bash
git add docker/apps/vrec-models-v1/Dockerfile
git commit -m "feat(vrec-models-v1): install FoundationStereo into env foundation_stereo"
```

---

### Task 5: Runtime Dockerfile — install pi3

**Files:**
- Modify: `docker/apps/vrec-models-v1/Dockerfile`

**Interfaces:**
- Consumes: env `pi3` from Task 3, `thirdparty/Pi3/` from build context
- Produces: `/app/pi3` populated, env has torch 2.5.1 cu124 + Pi3 deps + Pi3 installed editable

Mirrors `docker/Pi3/Dockerfile` lines 74–80.

- [ ] **Step 1: Append pi3 layer**

Replace the `# placeholder: pi3 follows` line with:

```dockerfile
COPY thirdparty/Pi3 /app/pi3

RUN conda run -n pi3 pip install --no-cache-dir \
        torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124 \
 && conda run -n pi3 pip install --no-cache-dir -r /app/pi3/requirements.txt \
 && conda run -n pi3 pip install --no-cache-dir -e /app/pi3 \
 && rm -rf /app/pi3/assets

# placeholder: vggt-omega follows
```

- [ ] **Step 2: Verify**

Run: `grep -n "/app/pi3" docker/apps/vrec-models-v1/Dockerfile`
Expected: at least 4 matches (COPY + 3 conda run).

- [ ] **Step 3: Commit**

```bash
git add docker/apps/vrec-models-v1/Dockerfile
git commit -m "feat(vrec-models-v1): install Pi3 into env pi3"
```

---

### Task 6: Runtime Dockerfile — install vggt-omega

**Files:**
- Modify: `docker/apps/vrec-models-v1/Dockerfile`

**Interfaces:**
- Consumes: env `vggt-omega` from Task 3, `thirdparty/vggt-omega/` from build context
- Produces: `/app/vggt-omega` populated, env has torch 2.6.0 cu126 + vggt-omega deps + editable install

Mirrors `docker/vggt-omega/Dockerfile` lines 76–81. Drops the HF download (weights mounted at runtime per global constraint).

- [ ] **Step 1: Append vggt-omega layer**

Replace the `# placeholder: vggt-omega follows` line with:

```dockerfile
COPY thirdparty/vggt-omega /app/vggt-omega

RUN conda run -n vggt-omega pip install --no-cache-dir \
        torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu126 \
 && conda run -n vggt-omega pip install --no-cache-dir -r /app/vggt-omega/requirements.txt \
 && conda run -n vggt-omega pip install --no-cache-dir -e /app/vggt-omega

# placeholder: sam3 follows
```

- [ ] **Step 2: Verify**

Run: `grep -n "/app/vggt-omega" docker/apps/vrec-models-v1/Dockerfile`
Expected: 4+ matches.

- [ ] **Step 3: Commit**

```bash
git add docker/apps/vrec-models-v1/Dockerfile
git commit -m "feat(vrec-models-v1): install vggt-omega into env vggt-omega"
```

---

### Task 7: Runtime Dockerfile — install sam3 + final CMD

**Files:**
- Modify: `docker/apps/vrec-models-v1/Dockerfile`

**Interfaces:**
- Consumes: env `sam3` from Task 3, `thirdparty/sam3/` from build context
- Produces: `/app/sam3` populated, env has torch 2.10.0 cu128 + sam3 editable + flash-attn-3. Final `CMD ["/bin/bash"]`. Empty `/opt/var/models/` directory created.

Mirrors `docker/sam3/Dockerfile` lines 73–82, drops HF model bake.

- [ ] **Step 1: Append sam3 layer + CMD**

Replace the `# placeholder: sam3 follows` line with:

```dockerfile
COPY thirdparty/sam3 /app/sam3

RUN conda run -n sam3 pip install --no-cache-dir \
        torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu128 \
 && conda run -n sam3 pip install --no-cache-dir -e "/app/sam3[notebooks]" \
 && conda run -n sam3 pip install --no-cache-dir einops ninja \
 && conda run -n sam3 pip install --no-cache-dir flash-attn-3 --no-deps --index-url https://download.pytorch.org/whl/cu128 \
 && rm -rf /app/sam3/examples /app/sam3/assets

RUN mkdir -p /opt/var/models

CMD ["/bin/bash"]
```

- [ ] **Step 2: Verify the file is complete**

Run: `tail -5 docker/apps/vrec-models-v1/Dockerfile`
Expected: ends with `CMD ["/bin/bash"]`.

Run: `grep -c "^COPY thirdparty/" docker/apps/vrec-models-v1/Dockerfile`
Expected: `4` (one per model).

- [ ] **Step 3: Commit**

```bash
git add docker/apps/vrec-models-v1/Dockerfile
git commit -m "feat(vrec-models-v1): install sam3 into env sam3 + CMD bash"
```

---

### Task 8: Dockerfile.dev — copy sam3 dev template

**Files:**
- Create: `docker/apps/vrec-models-v1/Dockerfile.dev`

**Interfaces:**
- Consumes: `${BASE_IMAGE}` build-arg (defaults to `ghcr.io/wangxinjian1108/vrec-models-v1:latest`)
- Produces: dev image with SSH(:22) + JupyterLab(:8888) + jovyan + root password `ShARC`

The template is identical across all dev images in this repo. Copy `docker/sam3/Dockerfile.dev` verbatim, then change only the `ARG BASE_IMAGE` default.

- [ ] **Step 1: Copy the template**

Run: `cp docker/sam3/Dockerfile.dev docker/apps/vrec-models-v1/Dockerfile.dev`

- [ ] **Step 2: Update the BASE_IMAGE default**

Edit `docker/apps/vrec-models-v1/Dockerfile.dev` — replace the first non-comment line:

From: `ARG BASE_IMAGE=ghcr.io/wangxinjian1108/sam3:latest`
To: `ARG BASE_IMAGE=ghcr.io/wangxinjian1108/vrec-models-v1:latest`

- [ ] **Step 3: Verify**

Run: `head -2 docker/apps/vrec-models-v1/Dockerfile.dev`
Expected:
```
ARG BASE_IMAGE=ghcr.io/wangxinjian1108/vrec-models-v1:latest
FROM ${BASE_IMAGE}
```

Run: `diff <(tail -n +2 docker/sam3/Dockerfile.dev) <(tail -n +2 docker/apps/vrec-models-v1/Dockerfile.dev)`
Expected: empty diff (only line 1 differs).

- [ ] **Step 4: Commit**

```bash
git add docker/apps/vrec-models-v1/Dockerfile.dev
git commit -m "feat(vrec-models-v1): add dev image (s6-overlay + SSH + JupyterLab)"
```

---

### Task 9: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/docker-vrec-models-v1.yml`

**Interfaces:**
- Consumes: secrets `GITHUB_TOKEN` (always), optional `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN`
- Produces: pushes `ghcr.io/wangxinjian1108/vrec-models-v1:{latest,sha-<7>,<branch>}` and `:dev,:dev-sha-<7>` on master

Mirrors `.github/workflows/docker-sam3.yml` exactly except:
- name + paths changed to `vrec-models-v1`
- four submodule paths instead of one
- no HF token (weights not baked)

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/docker-vrec-models-v1.yml`:

```yaml
name: Docker – vrec-models-v1

on:
  push:
    branches: [master]
    tags: ["v*.*.*"]
    paths:
      - "docker/apps/vrec-models-v1/**"
      - "thirdparty/FoundationStereo"
      - "thirdparty/Pi3"
      - "thirdparty/vggt-omega"
      - "thirdparty/sam3"
      - ".github/workflows/docker-vrec-models-v1.yml"
  pull_request:
    branches: [master]
    paths:
      - "docker/apps/vrec-models-v1/**"
      - "thirdparty/FoundationStereo"
      - "thirdparty/Pi3"
      - "thirdparty/vggt-omega"
      - "thirdparty/sam3"
      - ".github/workflows/docker-vrec-models-v1.yml"
  workflow_dispatch:

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          submodules: recursive
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Free disk space
        run: |
          sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc /opt/hostedtoolcache
          sudo rm -rf /usr/share/swift /usr/local/graalvm /usr/local/.ghcup
          sudo rm -rf /usr/local/share/powershell /usr/local/share/chromium
          sudo docker image prune -af
          df -h

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        if: github.event_name != 'pull_request' && env.DOCKERHUB_USERNAME != ''
        env:
          DOCKERHUB_USERNAME: ${{ secrets.DOCKERHUB_USERNAME }}
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Login to GHCR
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.repository_owner }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Docker metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: |
            name=${{ secrets.DOCKERHUB_USERNAME }}/vrec-models-v1,enable=${{ secrets.DOCKERHUB_USERNAME != '' }}
            ghcr.io/${{ github.repository_owner }}/vrec-models-v1
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix=sha-,format=short
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Set runtime base tag for dev image
        id: runtime-base
        run: |
          echo "remote=ghcr.io/${{ github.repository_owner }}/vrec-models-v1:sha-${GITHUB_SHA::7}" >> "$GITHUB_OUTPUT"

      - name: Build runtime image
        uses: docker/build-push-action@v6
        with:
          context: .
          file: docker/apps/vrec-models-v1/Dockerfile
          push: ${{ github.event_name != 'pull_request' }}
          tags: |
            ${{ steps.meta.outputs.tags }}
            ${{ steps.runtime-base.outputs.remote }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Docker metadata for dev image
        id: meta-dev
        uses: docker/metadata-action@v5
        with:
          images: |
            name=${{ secrets.DOCKERHUB_USERNAME }}/vrec-models-v1,enable=${{ secrets.DOCKERHUB_USERNAME != '' }}
            ghcr.io/${{ github.repository_owner }}/vrec-models-v1
          tags: |
            type=raw,value=dev
            type=sha,prefix=dev-sha-,format=short

      - name: Build dev image
        if: github.event_name != 'pull_request'
        uses: docker/build-push-action@v6
        with:
          context: .
          file: docker/apps/vrec-models-v1/Dockerfile.dev
          push: true
          build-args: |
            BASE_IMAGE=${{ steps.runtime-base.outputs.remote }}
          tags: ${{ steps.meta-dev.outputs.tags }}
          labels: ${{ steps.meta-dev.outputs.labels }}
          cache-from: type=gha,scope=dev
          cache-to: type=gha,mode=max,scope=dev
```

- [ ] **Step 2: Verify YAML parses**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/docker-vrec-models-v1.yml'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Verify path filter and image name**

Run: `grep -c "vrec-models-v1" .github/workflows/docker-vrec-models-v1.yml`
Expected: at least 10 occurrences (paths × 2, image refs, file path, etc.)

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/docker-vrec-models-v1.yml
git commit -m "ci(vrec-models-v1): add build + push workflow for runtime + dev images"
```

---

### Task 10: Push and monitor CI

**Files:**
- None (no source changes)

**Interfaces:**
- Consumes: all prior commits
- Produces: published images on GHCR

The first CI run is the real validation. The image is large (~25-30 GB estimated); GitHub-hosted runner disk may not be enough. If it fails, capture the failure mode and decide between (a) drop flash-attn compilation, (b) self-hosted runner, (c) local build + push.

- [ ] **Step 1: Push commits**

```bash
git push origin master
```

- [ ] **Step 2: Watch the workflow**

Run:
```bash
gh run watch --exit-status $(gh run list --workflow=docker-vrec-models-v1.yml --limit 1 --json databaseId --jq '.[0].databaseId')
```

Expected: workflow ends with `success`. If it fails, run `gh run view <id> --log-failed | tail -200` to see the failure mode.

- [ ] **Step 3: On success — verify the published images**

```bash
docker pull ghcr.io/wangxinjian1108/vrec-models-v1:latest
docker pull ghcr.io/wangxinjian1108/vrec-models-v1:dev
docker run --rm ghcr.io/wangxinjian1108/vrec-models-v1:latest \
  bash -lc "for e in foundation_stereo pi3 vggt-omega sam3; do conda run -n \$e python -c 'import torch; print(\"\${e}:\", torch.__version__)' || echo FAIL \$e; done"
```

Expected: four lines `<env>: <version>` printing torch 2.4.1 / 2.5.1 / 2.6.0 / 2.10.0.

- [ ] **Step 4: On failure — diagnose and pick fallback**

Read failure tail. Common failure modes and responses:

| Symptom | Likely cause | Response |
|---|---|---|
| `No space left on device` during build | Image too large for runner | Drop `flash-attn` install, or move to self-hosted |
| `flash-attn` build error | nvcc/torch ABI mismatch | Check `TORCH_CUDA_ARCH_LIST`; install with `--no-build-isolation` |
| `pip` resolver conflict in one env | Cross-env contamination | Re-confirm `conda run -n <env>` is used everywhere |
| Cache export fails after push succeeds | Azure SAS expired (>1h build) | Image is published; just re-run for cache, no fix needed |

Apply the smallest fix and re-push.

- [ ] **Step 5: On success — final commit (if any fixes were needed)**

If Step 4 required code changes, commit them and re-run from Step 2 until green.

---

## Self-Review

**Spec coverage:**
- Section 1 goal — Tasks 2–7 (runtime), Task 8 (dev), covered
- Section 2 layout `docker/apps/vrec-models-v1/` — Task 2 creates the dir, Task 8 adds dev — covered
- Section 3 base image `nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04` — Task 2 sets it — covered
- Section 4 in-image layout `/app/<name>` + four envs — Tasks 3–7 — covered
- Section 5 apt list including `libarchive-tools` + `netcat-openbsd` — Task 1 (skill) + Task 2 (this image) — both covered
- Section 6 build order — Tasks 2–7 follow it exactly — covered
- Section 7 Dockerfile.dev — Task 8 — covered
- Section 8 CI — Task 9 — covered, plus Task 10 validates
- Section 9 run examples — informational, no task needed
- Section 10 not-in-scope — respected (no weight bake, no entry script, no PPU, no skill abstraction)
- Section 11 acceptance — Task 10 step 3 covers the conda env smoke test; sam3/Pi3/etc demo runs are user-side post-merge

**Placeholder scan:** No "TBD"/"TODO"/"similar to". Each step has the exact code or command. Ok.

**Type/name consistency:** image name `vrec-models-v1` matches across spec, Dockerfile (base for dev), workflow tags, and runtime-base step. env names match across Tasks 3–7. paths `/app/{foundation_stereo,pi3,vggt-omega,sam3}` consistent. Ok.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-18-vrec-models-v1.md`.
