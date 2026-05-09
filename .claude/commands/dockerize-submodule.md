Dockerize a submodule: generate a minimal Dockerfile and GitHub Actions workflow for it.

## Argument
`$ARGUMENTS` is the submodule path or name (e.g. `thirdparty/Scal3R` or just `Scal3R`).

## Steps

1. **Locate the submodule** — search `.gitmodules` to resolve the full path if only a name was given. Read the submodule directory to understand the project type.

2. **Detect project type, Python version & CUDA version** — check for `pyproject.toml`, `requirements.txt`, `package.json`, `go.mod`, `Cargo.toml`, `pom.xml`, etc. Read the relevant file AND the README and any install scripts to understand dependencies, entry points, and version requirements:
   - **Python version**: read `requires-python` in `pyproject.toml`, or explicit version in install scripts / README. If not specified, default to 3.11.
   - **CUDA version**: look for explicit mentions in README, install scripts, or `requirements.txt` (e.g. `torch` index URLs like `cu118`, `cu126`, `cu128`). If not found, default to CUDA 12.6.
   - Map the required CUDA version to the appropriate official image tag: `nvidia/cuda:<cuda-version>-cudnn-devel-ubuntu22.04` (e.g. CUDA 11.8 → `nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04`, CUDA 12.1 → `nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04`, CUDA 12.6 → `nvidia/cuda:12.6.3-cudnn-devel-ubuntu22.04`, CUDA 12.8 → `nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04`)
   - Use the detected CUDA version to pick the correct PyTorch wheel index URL (cu118 / cu126 / cu128)
   - Use the detected Python version when creating the conda env

3. **Create the Dockerfile** — write `docker/<repo-name>/Dockerfile` (repo-name is the last path segment of the submodule, create the directory if it doesn't exist). Follow this structure exactly, in order:

   **a. Base image & ENV block**
   - Use the CUDA base image selected in step 2
   - Set these ENV vars in a single `ENV` instruction:
     ```dockerfile
     ENV DEBIAN_FRONTEND=noninteractive \
         PYTHONDONTWRITEBYTECODE=1 \
         PYTHONUNBUFFERED=1 \
         PIP_NO_CACHE_DIR=1 \
         CONDA_DIR=/opt/conda \
         CONDA_ENV=<repo-name>
     ```

   **b. WORKDIR**
   - Set `WORKDIR` to `/<repo-name>`

   **c. apt packages**
   - Install this fixed base set of packages (always include all of them), **one package per line**, then clean up:
     ```dockerfile
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
         && rm -rf /var/lib/apt/lists/*
     ```
   - Thoroughly inspect all available sources to determine which extra system packages are needed — read ALL of the following that exist:
     - `pyproject.toml`, `requirements.txt`, `setup.py`, `setup.cfg`
     - `README.md`, `docs/install.md` and any other docs files
     - Install scripts (`scripts/install.sh`, `Makefile`, etc.)
     - Any CI config files (`.github/workflows/*.yml`, `.travis.yml`, `Dockerfile` if present)
   - Map Python dependencies to their system-level requirements. Common examples:
     - `opencv-python`, `open3d` → `libgl1`, `libglib2.0-0`
     - `opencv-python` with display → also `libsm6`, `libxext6`, `libxrender-dev`
     - `soundfile`, `librosa` → `libsndfile1`
     - `numba`, `faiss` → `libgomp1`
     - `pyopengl` → `libgl1`, `libglu1-mesa`
   - Do not add packages that are not required by the project

   **d. Miniconda + conda env**
   - Install Miniconda, accept TOS for both default channels (without `--override-channels`), create the conda env, clean cache — all in one `RUN` layer:
     ```dockerfile
     RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
         && bash /tmp/miniconda.sh -b -p "${CONDA_DIR}" \
         && rm -f /tmp/miniconda.sh \
         && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/main \
         && "${CONDA_DIR}/bin/conda" tos accept --channel https://repo.anaconda.com/pkgs/r \
         && "${CONDA_DIR}/bin/conda" create -n "${CONDA_ENV}" python=<detected-python-version> -y \
         && "${CONDA_DIR}/bin/conda" clean -afy
     ```

   **e. SSH host keys**
   ```dockerfile
   RUN mkdir -p /var/run/sshd /root/.ssh \
       && ssh-keygen -A
   ```

   **f. PATH**
   ```dockerfile
   ENV PATH=${CONDA_DIR}/envs/${CONDA_ENV}/bin:${CONDA_DIR}/bin:${PATH}
   ```

   **g. Copy submodule & install dependencies**
   - All submodules are available in the build context (repo root). Use `COPY <submodule-path> .` to copy the target submodule, and `COPY <other-submodule-path> <other-submodule-path>` for any dependency submodules — do NOT use `git clone` or `pip install git+https://` during build
   - Read the submodule's README and install scripts to understand the correct install order (e.g. torch before requirements.txt). Use `conda run -n "${CONDA_ENV}"` for all pip/python commands
   - Install dependencies, then **remove source directories in the same `RUN` layer** to keep the image clean

   **h. Model download**
   - Read the README and docs to find all model/checkpoint downloads (HuggingFace, GitHub releases, direct URLs, etc.)
   - If the repo mentions downloadable models, add **actual** (not commented) `RUN` steps to download them into `/opt/var/models/`
   - All models go to `/opt/var/models/<model-name>` regardless of where the repo's README says to put them
   - For HuggingFace models that require authentication, use BuildKit secret (token never baked into image layers):
     ```dockerfile
     RUN --mount=type=secret,id=hf_token \
         hf download <org>/<repo> <file> \
             --repo-type model --local-dir /opt/var/models/<model-name> \
             --token $(cat /run/secrets/hf_token)
     ```
   - For public downloads (GitHub releases, direct URLs):
     ```dockerfile
     RUN mkdir -p /opt/var/models/<model-name> && \
         curl -L <url> -o /opt/var/models/<model-name>/<filename>
     ```
   - If any model uses HF secret, the workflow's `build-push-action` must include:
     ```yaml
     secrets: |
       hf_token=${{ secrets.HF_TOKEN }}
     ```
   - If no models are mentioned in the README, skip this step entirely (do not add commented templates)

   **i. CMD / ENTRYPOINT**
   - Define a minimal `CMD` or `ENTRYPOINT` that actually runs the project (use the entry point from pyproject.toml scripts, package.json main, etc.)

3.5. **Ask about Zelos Harbor** — use AskUserQuestion to ask the user whether to also push to Zelos Harbor (`harbor-volc.zelostech.com.cn:5443`). If yes, the image will be pushed to `harbor-volc.zelostech.com.cn:5443/zcloud_auto/<repo-name>:<tag>` by default. This will be used in step 4 to add Harbor login, tag, and push steps.

4. **Create the GitHub Actions workflow** — write `.github/workflows/docker-<repo-name>.yml`. Use this structure:
   - Trigger on: push to `master` (tags `v*.*.*`), PR to `master`, `workflow_dispatch`. Add `paths` filter to both push and pull_request so only relevant changes trigger the build:
     ```yaml
     paths:
       - "docker/<repo-name>/**"
       - "thirdparty/<submodule-path>"
       - ".github/workflows/docker-<repo-name>.yml"
     ```
   - Single job `build-and-push` with `ubuntu-latest` and explicit permissions:
     ```yaml
     permissions:
       contents: read
       packages: write
     ```
   - Steps in order:
     1. `actions/checkout@v4` with `submodules: recursive`
     2. Free disk space (required for large CUDA base images):
        ```yaml
        - name: Free disk space
          run: |
            sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc /opt/hostedtoolcache
            sudo docker image prune -af
            df -h
        ```
     3. `docker/setup-buildx-action@v3`
     4. Login to Docker Hub — skip on PR **and** when secret is empty:
        ```yaml
        - name: Login to Docker Hub
          if: github.event_name != 'pull_request' && env.DOCKERHUB_USERNAME != ''
          env:
            DOCKERHUB_USERNAME: ${{ secrets.DOCKERHUB_USERNAME }}
          uses: docker/login-action@v3
          with:
            username: ${{ secrets.DOCKERHUB_USERNAME }}
            password: ${{ secrets.DOCKERHUB_TOKEN }}
        ```
     5. Login to ghcr.io — skip on PR (`secrets.GITHUB_TOKEN` always available)
     6. **(If Harbor enabled)** Login to Zelos Harbor — skip on PR and when secret is empty:
        ```yaml
        - name: Login to Zelos Harbor
          if: github.event_name != 'pull_request' && env.HARBOR_USERNAME != ''
          env:
            HARBOR_USERNAME: ${{ secrets.HARBOR_USERNAME }}
          run: echo "${{ secrets.HARBOR_PASSWORD }}" | docker login harbor-volc.zelostech.com.cn:5443 --username=${{ secrets.HARBOR_USERNAME }} --password-stdin
        ```
     7. `docker/metadata-action@v5` with images:
        - `name=${{ secrets.DOCKERHUB_USERNAME }}/<repo-name>,enable=${{ secrets.DOCKERHUB_USERNAME != '' }}`
        - `ghcr.io/${{ github.repository_owner }}/<repo-name>`
        - **(If Harbor enabled)** `name=harbor-volc.zelostech.com.cn:5443/zcloud_auto/<repo-name>,enable=${{ secrets.HARBOR_USERNAME != '' }}`
     8. Tags: `type=ref,event=branch`, `type=semver,pattern={{version}}`, `type=semver,pattern={{major}}.{{minor}}`, `type=sha,prefix=sha-,format=short`, `type=raw,value=latest,enable={{is_default_branch}}`
     9. `docker/build-push-action@v6` with `context: .` (repo root, so all submodules are available), `file: docker/<repo-name>/Dockerfile`, GHA cache, push only when not PR. Buildx pushes to all registries listed in metadata-action in one shot — do NOT use `docker tag` + `docker push` separately.

5. **Report** — after writing both files, print a one-line summary: what Dockerfile base was chosen and why, and the workflow file path.
