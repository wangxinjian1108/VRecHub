Dockerize a submodule: generate a minimal Dockerfile, Dockerfile.dev (SSH + Jupyter dev layer), and GitHub Actions workflow for it.

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
         libarchive-tools \
         netcat-openbsd \
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

   **d. Generate locales**
   - The `locales` apt package alone does not generate any locale — without this step `locale -a` only shows `C`/`POSIX` and any process that inherits `LANG=en_US.UTF-8` from the host (e.g. K8s notebook) emits `Setting locale failed` warnings.
   - Generate en_US.UTF-8 and zh_CN.UTF-8 (Chinese path/filename support), then set the env vars. **Place the `ENV` block AFTER `locale-gen`** so subsequent RUN steps (miniconda, pip) don't run with a not-yet-generated locale:
     ```dockerfile
     RUN locale-gen en_US.UTF-8 zh_CN.UTF-8 \
         && update-locale LANG=en_US.UTF-8

     ENV LANG=en_US.UTF-8 \
         LANGUAGE=en_US:en \
         LC_ALL=en_US.UTF-8
     ```

   **e. Miniconda + conda env**
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

   **f. SSH host keys**
   ```dockerfile
   RUN mkdir -p /var/run/sshd /root/.ssh \
       && ssh-keygen -A
   ```

   **g. PATH**
   ```dockerfile
   ENV PATH=${CONDA_DIR}/envs/${CONDA_ENV}/bin:${CONDA_DIR}/bin:${PATH}
   ```

   **h. Copy submodule & install dependencies**
   - All submodules are available in the build context (repo root). Use `COPY <submodule-path> .` to copy the target submodule, and `COPY <other-submodule-path> <other-submodule-path>` for any dependency submodules — do NOT use `git clone` or `pip install git+https://` during build
   - Read the submodule's README and install scripts to understand the correct install order (e.g. torch before requirements.txt). Use `conda run -n "${CONDA_ENV}"` for all pip/python commands
   - Install dependencies, then **remove source directories in the same `RUN` layer** to keep the image clean

   **i. Model download**
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

   **j. CMD / ENTRYPOINT**
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
            sudo rm -rf /usr/share/swift /usr/local/graalvm /usr/local/.ghcup
            sudo rm -rf /usr/local/share/powershell /usr/local/share/chromium
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
     9. Set runtime base tag for dev image:
        ```yaml
        - name: Set runtime base tag for dev image
          id: runtime-base
          run: |
            echo "remote=ghcr.io/${{ github.repository_owner }}/<repo-name>:sha-${GITHUB_SHA::7}" >> "$GITHUB_OUTPUT"
        ```
     10. `docker/build-push-action@v6` for **runtime image** with `context: .` (repo root, so all submodules are available), `file: docker/<repo-name>/Dockerfile`, GHA cache, push only when not PR. Include the `${{ steps.runtime-base.outputs.remote }}` tag in addition to the metadata tags. Buildx pushes to all registries listed in metadata-action in one shot — do NOT use `docker tag` + `docker push` separately. If model download uses HF secret, add:
        ```yaml
        secrets: |
          hf_token=${{ secrets.HF_TOKEN }}
        ```
     11. Docker metadata for dev image:
        ```yaml
        - name: Docker metadata for dev image
          id: meta-dev
          uses: docker/metadata-action@v5
          with:
            images: |
              name=${{ secrets.DOCKERHUB_USERNAME }}/<repo-name>,enable=${{ secrets.DOCKERHUB_USERNAME != '' }}
              ghcr.io/${{ github.repository_owner }}/<repo-name>
            tags: |
              type=raw,value=dev
              type=sha,prefix=dev-sha-,format=short
        ```
     12. `docker/build-push-action@v6` for **dev image** — only when not PR:
        ```yaml
        - name: Build dev image
          if: github.event_name != 'pull_request'
          uses: docker/build-push-action@v6
          with:
            context: .
            file: docker/<repo-name>/Dockerfile.dev
            push: true
            build-args: |
              BASE_IMAGE=${{ steps.runtime-base.outputs.remote }}
            tags: ${{ steps.meta-dev.outputs.tags }}
            labels: ${{ steps.meta-dev.outputs.labels }}
            cache-from: type=gha,scope=dev
            cache-to: type=gha,mode=max,scope=dev
        ```

4.5. **Create `Dockerfile.dev`** — write `docker/<repo-name>/Dockerfile.dev`. This is a standard dev layer on top of the runtime image, providing SSH + JupyterLab via s6-overlay. Use this exact template (only change the `BASE_IMAGE` default to match `ghcr.io/wangxinjian1108/<repo-name-lowercase>:latest`):

   ```dockerfile
   ARG BASE_IMAGE=ghcr.io/wangxinjian1108/<repo-name-lowercase>:latest
   FROM ${BASE_IMAGE}

   ARG S6_OVERLAY_VERSION=3.2.0.2
   ARG JUPYTER_PORT=8888
   ARG SSH_PORT=22
   ARG NB_USER=jovyan
   ARG NB_UID=1000
   ARG NB_GID=100
   ARG WORK_DIR=/home/${NB_USER}
   ARG ROOT_PASSWORD=ShARC

   ENV DEBIAN_FRONTEND=noninteractive \
       NB_USER=${NB_USER} \
       NB_UID=${NB_UID} \
       NB_GID=${NB_GID} \
       HOME=${WORK_DIR} \
       JUPYTER_PORT=${JUPYTER_PORT} \
       SSH_PORT=${SSH_PORT} \
       NB_PREFIX=/ \
       SHELL=/bin/bash

   # s6-overlay
   ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp
   ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz /tmp
   RUN tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz && \
       tar -C / -Jxpf /tmp/s6-overlay-x86_64.tar.xz && \
       rm -f /tmp/s6-overlay-*.tar.xz

   # System packages
   RUN apt-get update && apt-get install -y --no-install-recommends \
       openssh-server \
       openssh-client \
       sudo \
       git curl wget vim htop tmux \
       build-essential cmake \
       python3-pip python3-dev \
       && rm -rf /var/lib/apt/lists/*

   # SSH
   RUN mkdir -p /var/run/sshd && \
       sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config && \
       sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
       sed -i 's/#PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config && \
       sed -i 's/#UsePAM.*/UsePAM yes/' /etc/ssh/sshd_config && \
       if awk -F: '$1 == "root" { exit !($2 == "" || $2 == "!" || $2 == "*") }' /etc/shadow; then \
           echo "root:${ROOT_PASSWORD}" | chpasswd; \
       fi

   # Notebook user
   RUN if ! getent group "${NB_GID}" >/dev/null; then \
           groupadd -g "${NB_GID}" "${NB_USER}"; \
       fi && \
       existing_user=$(getent passwd "${NB_UID}" | cut -d: -f1 || true) && \
       if [ -n "$existing_user" ] && [ "$existing_user" != "${NB_USER}" ]; then \
           usermod -l "${NB_USER}" -d "${WORK_DIR}" -m "$existing_user" 2>/dev/null || true; \
           usermod -g "${NB_GID}" "${NB_USER}" 2>/dev/null || true; \
       elif ! id -u "${NB_USER}" >/dev/null 2>&1; then \
           useradd -m -s /bin/bash -u "${NB_UID}" -g "${NB_GID}" "${NB_USER}"; \
       fi && \
       mkdir -p "${WORK_DIR}" && \
       chown -R "${NB_UID}:${NB_GID}" "${WORK_DIR}" && \
       echo "${NB_USER} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${NB_USER} && \
       chmod 0440 /etc/sudoers.d/${NB_USER}

   # SSH key for the notebook user
   RUN mkdir -p ${WORK_DIR}/.ssh /root/.ssh && \
       if [ ! -f ${WORK_DIR}/.ssh/id_rsa ]; then \
           ssh-keygen -t rsa -b 4096 -N "" -f ${WORK_DIR}/.ssh/id_rsa; \
       fi && \
       cp ${WORK_DIR}/.ssh/id_rsa.pub ${WORK_DIR}/.ssh/authorized_keys && \
       chown -R ${NB_UID}:${NB_GID} ${WORK_DIR}/.ssh && \
       chmod 700 ${WORK_DIR}/.ssh && \
       chmod 600 ${WORK_DIR}/.ssh/id_rsa ${WORK_DIR}/.ssh/authorized_keys && \
       chmod 644 ${WORK_DIR}/.ssh/id_rsa.pub

   # Python / Jupyter
   RUN python -m pip install --no-cache-dir jupyterlab ipywidgets

   # s6 service: jupyter
   RUN mkdir -p /etc/services.d/jupyter
   COPY <<'EOF' /etc/services.d/jupyter/run
   #!/command/with-contenv bash
   set -e
   cd "${HOME:-/home/jovyan}"
   exec s6-setuidgid "${NB_USER}" jupyter lab \
     --ip=0.0.0.0 \
     --port="${JUPYTER_PORT:-8888}" \
     --no-browser \
     --ServerApp.base_url="${NB_PREFIX:-/}" \
     --ServerApp.root_dir="${HOME:-/home/jovyan}" \
     --ServerApp.token="" \
     --ServerApp.password=""
   EOF
   RUN chmod +x /etc/services.d/jupyter/run

   # s6 service: ssh
   RUN mkdir -p /etc/services.d/ssh
   COPY <<'EOF' /etc/services.d/ssh/run
   #!/command/with-contenv bash
   set -e
   exec /usr/sbin/sshd -D -e
   EOF
   RUN chmod +x /etc/services.d/ssh/run

   WORKDIR ${WORK_DIR}

   EXPOSE ${JUPYTER_PORT} ${SSH_PORT}

   ENTRYPOINT ["/init"]
   ```

5. **Report** — after writing all files, print a one-line summary: what Dockerfile base was chosen and why, and the workflow file path.
