# vrec-models-train-v1 — sam3 训练依赖增量镜像

**状态**: 已批准，待实现
**日期**: 2026-06-23

## 1. 目标

提供 `ghcr.io/wangxinjian1108/vrec-models-train-v1`（runtime + dev），在 `vrec-models-v1:latest` 之上仅给 sam3 conda env 增量安装 `[train]` extras。其余三个 env (fast-foundationstereo / pi3 / vggt-omega) 保持不变 —— 它们各自的训练依赖要么已包含在现有 `requirements.txt` 中（pi3），要么 upstream 未公开训练栈（fast-foundationstereo / vggt-omega）。

产出 tag：
- `:latest` — runtime, CMD = `bash`
- `:dev` — FROM runtime + s6-overlay + SSH + JupyterLab

## 2. 仓库布局

```
docker/apps/vrec-models-train-v1/
├── Dockerfile        # FROM vrec-models-v1:latest + sam3 [train]
└── Dockerfile.dev    # 复用 dev 模板
.github/workflows/
└── docker-vrec-models-train-v1.yml
```

与 `docker/apps/vrec-models-v1/` 平级。命名约定：当一个聚合 image 有衍生变体（推理 → 训练）时，加 `-train` 后缀（同 sam3 vs sam3-train 的 pattern）。

## 3. Base 镜像

`ghcr.io/wangxinjian1108/vrec-models-v1:latest`

由 `docker-vrec-models-v1.yml` 维护。后者 sha 变化 → 通过 `workflow_run` 串联触发本镜像 rebuild。

## 4. Runtime Dockerfile

```dockerfile
ARG BASE_IMAGE=ghcr.io/wangxinjian1108/vrec-models-v1:latest
FROM ${BASE_IMAGE}

# Add sam3 [train] extras on top of the inherited [notebooks] install:
#   hydra-core, submitit, tensorboard, zstandard, scipy,
#   torchmetrics, fvcore, fairscale, scikit-image, scikit-learn
# Note: vrec-models-v1 lays out sam3 at /app/sam3 (NOT /sam3 like the
# standalone sam3 image — different layout convention per image family).
RUN cd /app/sam3 && conda run -n sam3 pip install --no-cache-dir -e ".[train]"

CMD ["/bin/bash"]
```

注意：与单独的 sam3-train 不同——
- sam3-train 的 base 是 `sam3:latest`，sam3 源码在 `/sam3`
- vrec-models-train-v1 的 base 是 `vrec-models-v1:latest`，sam3 源码在 `/app/sam3`（spec §4 of vrec-models-v1 design）

## 5. Dockerfile.dev

`FROM ${BASE_IMAGE:-ghcr.io/wangxinjian1108/vrec-models-train-v1:latest}` + 现有 s6+SSH+JupyterLab 模板（与已有 7 个 dev 镜像一致，仅改 line 1 default）。

## 6. CI workflow

`.github/workflows/docker-vrec-models-train-v1.yml`：

- **触发**：
  - `workflow_run` on `Docker – vrec-models-v1` `completed` (branches: master) → 守卫 `if: conclusion=='success'`
  - `push` to master + tags + paths（`docker/apps/vrec-models-train-v1/**` + 自身 yml）
  - `pull_request` 同 paths
  - `workflow_dispatch`
- **不触发的 path**：`thirdparty/sam3`（源码改动通过 `docker-sam3.yml → docker-vrec-models-v1.yml → docker-vrec-models-train-v1.yml` 链路传导）
- **checkout**: `actions/checkout@v4` 不带 submodules（image 不 COPY 任何 thirdparty 源码）
- **不带 hf_token**
- runtime tag: `latest`, `sha-<7>`, `<branch>`, `v*.*.*`
- dev tag: `dev`, `dev-sha-<7>`
- runtime cache 默认 scope，dev cache scope=dev

整体结构与 `docker-sam3-train.yml` 同构，差异只是 image name 和 upstream workflow name。

## 7. 不在范围内

- fast-foundationstereo / pi3 / vggt-omega 的额外训练依赖（pi3 已有；其他 upstream 未提供）
- sam3 `[dev]` extras（pytest / black / ruff —— 不属于训练运行依赖）
- 多机分布式（MPI / NCCL CLI）系统包
- 模型权重 baking（继承 base 的策略：运行时挂载）

## 8. 验收标准

- `docker pull ghcr.io/wangxinjian1108/vrec-models-train-v1:latest` 成功
- 镜像内 `conda run -n sam3 python -c "import hydra, submitit, tensorboard, fvcore, fairscale, torchmetrics; print('sam3 train deps OK')"` 通过
- 其余 env 推理仍然 OK：`for e in fast-foundationstereo pi3 vggt-omega sam3; do conda run -n "$e" python -c "import torch; print('$e:', torch.__version__)"; done`
- `:dev` SSH（root:ShARC）+ JupyterLab(:8888) 可用
- `Docker – vrec-models-v1` 跑完成功后，`Docker – vrec-models-train-v1` 自动触发并最终成功

---

# vrec-models-train-v1 Implementation Plan

> Use superpowers:subagent-driven-development to execute task-by-task. Steps use `- [ ]` checkbox tracking.

**Goal:** Build `ghcr.io/wangxinjian1108/vrec-models-train-v1:{latest,dev}` — a layered image FROM `vrec-models-v1:latest` adding sam3 `[train]` extras, with paired :dev image and CI chained after `Docker – vrec-models-v1`.

**Architecture:** Two-line runtime Dockerfile + standard dev layer + workflow_run-chained CI. Mirrors the `sam3-train` pattern but adapted for the multi-env aggregate image's `/app/sam3` source layout.

**Tech Stack:** Docker buildx, GitHub Actions, workflow_run trigger, sam3 `[train]` extras (hydra-core / submitit / tensorboard / zstandard / scipy / torchmetrics / fvcore / fairscale / scikit-image / scikit-learn).

## Global Constraints

- Image path: `docker/apps/vrec-models-train-v1/`
- Image name: `ghcr.io/wangxinjian1108/vrec-models-train-v1` + Docker Hub mirror via `${{ secrets.DOCKERHUB_USERNAME }}/vrec-models-train-v1`
- Base for runtime: `ghcr.io/wangxinjian1108/vrec-models-v1:latest` (overridable via `ARG BASE_IMAGE`)
- Base for dev: `ghcr.io/wangxinjian1108/vrec-models-train-v1:latest` (overridable via `ARG BASE_IMAGE`)
- Runtime tags: `latest`, `sha-<7>`, `<branch>`, `v*.*.*`. Dev tags: `dev`, `dev-sha-<7>`.
- Runtime CMD: `["/bin/bash"]`
- Dev image: s6-overlay v3.2.0.2 + SSH(:22) + JupyterLab(:8888) + jovyan UID=1000 GID=100 + root password `ShARC`
- New extras: sam3 `[train]` only (other envs unchanged)
- Source path inside base: `/app/sam3` (NOT `/sam3`)
- pip syntax: `cd /app/sam3 && conda run -n sam3 pip install --no-cache-dir -e ".[train]"` (proven pattern; pip rejects bare `<abs-path>[extras]`)
- No HF token in workflow (weights inherited)
- No submodule init in workflow (image doesn't COPY any thirdparty source)
- Workflow trigger: `workflow_run` on `Docker – vrec-models-v1` `completed` + paths-filtered push/PR + `workflow_dispatch`
- `workflow_run`-triggered job MUST guard with `if: github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success'`
- Push remote: `ssh://git@ssh.github.com:443/wangxinjian1108/VRecHub.git`

## File Structure

**Created:**
- `docker/apps/vrec-models-train-v1/Dockerfile` — runtime image (4 instructions: ARG, FROM, RUN, CMD)
- `docker/apps/vrec-models-train-v1/Dockerfile.dev` — dev layer (verbatim from `docker/sam3/Dockerfile.dev` except line 1)
- `.github/workflows/docker-vrec-models-train-v1.yml` — CI

**Modified:** none

---

### Task 1: Runtime Dockerfile

**Files:** Create `docker/apps/vrec-models-train-v1/Dockerfile`

**Interfaces:**
- Consumes: `${BASE_IMAGE}` defaulting to `ghcr.io/wangxinjian1108/vrec-models-v1:latest`. Base carries 4 conda envs and sam3 source at `/app/sam3` editable-installed with `[notebooks]` extras.
- Produces: `ghcr.io/wangxinjian1108/vrec-models-train-v1:latest` — same as base plus sam3 `[train]` extras in env `sam3`. Used as base for Task 2 dev build and Task 3 runtime publish.

- [ ] **Step 1: Create the directory and Dockerfile**

```dockerfile
ARG BASE_IMAGE=ghcr.io/wangxinjian1108/vrec-models-v1:latest
FROM ${BASE_IMAGE}

# Add sam3 [train] extras on top of the inherited [notebooks] install:
#   hydra-core, submitit, tensorboard, zstandard, scipy,
#   torchmetrics, fvcore, fairscale, scikit-image, scikit-learn
RUN cd /app/sam3 && conda run -n sam3 pip install --no-cache-dir -e ".[train]"

CMD ["/bin/bash"]
```

- [ ] **Step 2: Verify**

```bash
cat docker/apps/vrec-models-train-v1/Dockerfile
grep -c "^FROM\|^RUN\|^CMD\|^ARG" docker/apps/vrec-models-train-v1/Dockerfile  # expect 4
```

- [ ] **Step 3: Commit**

```bash
git add docker/apps/vrec-models-train-v1/Dockerfile
git commit -m "feat(vrec-models-train-v1): add runtime Dockerfile (FROM vrec-models-v1:latest + sam3 [train] extras)"
```

---

### Task 2: Dev Dockerfile

**Files:** Create `docker/apps/vrec-models-train-v1/Dockerfile.dev`

**Interfaces:**
- Consumes: `${BASE_IMAGE}` defaulting to `ghcr.io/wangxinjian1108/vrec-models-train-v1:latest`
- Produces: dev image with SSH(:22) + JupyterLab(:8888)

Plan-mandated verbatim duplication of the existing dev template (8 such files now in repo). Do not refactor.

- [ ] **Step 1: Copy template**

```bash
cp docker/sam3/Dockerfile.dev docker/apps/vrec-models-train-v1/Dockerfile.dev
```

- [ ] **Step 2: Update line 1 default**

Replace line 1 `ARG BASE_IMAGE=ghcr.io/wangxinjian1108/sam3:latest` with `ARG BASE_IMAGE=ghcr.io/wangxinjian1108/vrec-models-train-v1:latest`.

- [ ] **Step 3: Verify**

```bash
head -2 docker/apps/vrec-models-train-v1/Dockerfile.dev   # expect vrec-models-train-v1:latest
diff <(tail -n +2 docker/sam3/Dockerfile.dev) <(tail -n +2 docker/apps/vrec-models-train-v1/Dockerfile.dev)  # empty
```

- [ ] **Step 4: Commit**

```bash
git add docker/apps/vrec-models-train-v1/Dockerfile.dev
git commit -m "feat(vrec-models-train-v1): add dev image (s6-overlay + SSH + JupyterLab)"
```

---

### Task 3: GitHub Actions workflow

**Files:** Create `.github/workflows/docker-vrec-models-train-v1.yml`

**Interfaces:**
- Consumes: secrets `GITHUB_TOKEN`, optional `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN`. Triggered by `workflow_run` on `Docker – vrec-models-v1` `completed` + paths/dispatch backstops.
- Produces: pushes `ghcr.io/wangxinjian1108/vrec-models-train-v1:{latest,sha-<7>,<branch>,dev,dev-sha-<7>}` on master.

- [ ] **Step 1: Create the workflow**

```yaml
name: Docker – vrec-models-train-v1

on:
  workflow_run:
    workflows: ["Docker – vrec-models-v1"]
    types: [completed]
    branches: [master]
  push:
    branches: [master]
    tags: ["v*.*.*"]
    paths:
      - "docker/apps/vrec-models-train-v1/**"
      - ".github/workflows/docker-vrec-models-train-v1.yml"
  pull_request:
    branches: [master]
    paths:
      - "docker/apps/vrec-models-train-v1/**"
      - ".github/workflows/docker-vrec-models-train-v1.yml"
  workflow_dispatch:

jobs:
  build-and-push:
    if: ${{ github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
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
            name=${{ secrets.DOCKERHUB_USERNAME }}/vrec-models-train-v1,enable=${{ secrets.DOCKERHUB_USERNAME != '' }}
            ghcr.io/${{ github.repository_owner }}/vrec-models-train-v1
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix=sha-,format=short
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Set runtime base tag for dev image
        id: runtime-base
        run: |
          echo "remote=ghcr.io/${{ github.repository_owner }}/vrec-models-train-v1:sha-${GITHUB_SHA::7}" >> "$GITHUB_OUTPUT"

      - name: Build runtime image
        uses: docker/build-push-action@v6
        with:
          context: .
          file: docker/apps/vrec-models-train-v1/Dockerfile
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
            name=${{ secrets.DOCKERHUB_USERNAME }}/vrec-models-train-v1,enable=${{ secrets.DOCKERHUB_USERNAME != '' }}
            ghcr.io/${{ github.repository_owner }}/vrec-models-train-v1
          tags: |
            type=raw,value=dev
            type=sha,prefix=dev-sha-,format=short

      - name: Build dev image
        if: github.event_name != 'pull_request'
        uses: docker/build-push-action@v6
        with:
          context: .
          file: docker/apps/vrec-models-train-v1/Dockerfile.dev
          push: true
          build-args: |
            BASE_IMAGE=${{ steps.runtime-base.outputs.remote }}
          tags: ${{ steps.meta-dev.outputs.tags }}
          labels: ${{ steps.meta-dev.outputs.labels }}
          cache-from: type=gha,scope=dev
          cache-to: type=gha,mode=max,scope=dev
```

- [ ] **Step 2: Verify YAML**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/docker-vrec-models-train-v1.yml'))" && echo OK
grep -c "vrec-models-train-v1" .github/workflows/docker-vrec-models-train-v1.yml  # expect ≥10
grep -F "github.event.workflow_run.conclusion == 'success'" .github/workflows/docker-vrec-models-train-v1.yml  # expect 1 match
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/docker-vrec-models-train-v1.yml
git commit -m "ci(vrec-models-train-v1): add build + push workflow chained after docker-vrec-models-v1"
```

---

### Task 4: Push and verify CI

- [ ] **Step 1: Push**

```bash
git push ssh://git@ssh.github.com:443/wangxinjian1108/VRecHub.git master
```

- [ ] **Step 2: Watch the workflow**

```bash
sleep 8 && gh run list --workflow=docker-vrec-models-train-v1.yml --limit 1 --json databaseId,status,headSha
```

Capture databaseId, then poll until terminal:

```bash
TOKEN=$(gh auth token)
while true; do
  curl -s -H "Authorization: bearer $TOKEN" "https://api.github.com/repos/wangxinjian1108/VRecHub/actions/runs/<id>" -o /tmp/run.json
  python3 -c "import json; d=json.load(open('/tmp/run.json')); print('status=%s conclusion=%s' % (d.get('status'), d.get('conclusion')))"
  python3 -c "import json,sys; d=json.load(open('/tmp/run.json')); sys.exit(0 if d.get('status')=='completed' else 1)" && break
  sleep 60
done
```

- [ ] **Step 3: On success — done**

If success, the goal is satisfied — just confirm via package list. (Skip local pull — past observations show GHCR throughput on this network is too slow for 30+GB images; CI build success is the verification.)

- [ ] **Step 4: On failure — diagnose**

| Symptom | Likely cause | Response |
|---|---|---|
| `cd: can't cd to /app/sam3` | Wrong layout assumption | Verify with `docker run --rm $BASE_IMAGE ls -d /app/sam3` |
| pip resolver conflict | `[train]` extras vs `[notebooks]` extras (e.g. duplicate scipy/scikit-* versions) | Pin conflicting package |
| Workflow doesn't trigger | paths filter too narrow | Confirm `paths` includes `docker/apps/vrec-models-train-v1/**` |
| `if:` guard rejects event | Upstream workflow_run failed | Check `gh run view <id>` for guard rejection — re-run upstream first |

---

## Self-Review

**Spec coverage:**
- §1 goal — Tasks 1+2+3 — covered
- §2 layout — Tasks 1, 2, 3 — covered
- §3 base = vrec-models-v1:latest — Task 1 ARG default — covered
- §4 runtime Dockerfile (4 lines) — Task 1 — covered
- §5 Dockerfile.dev verbatim — Task 2 — covered
- §6 CI with workflow_run + if guard + no HF token + no submodule init — Task 3 — covered
- §7 not in scope — respected
- §8 acceptance — Task 4 step 2/3 covers CI green; image-internal smoke is post-merge user-side

**Placeholder scan:** No TBD/TODO. All commands and code blocks present.

**Type / name consistency:** `vrec-models-train-v1` consistent across Dockerfile ARG, Dockerfile.dev ARG, workflow tags, runtime-base step, and verification commands. Upstream workflow name `"Docker – vrec-models-v1"` (em-dash, matches docker-vrec-models-v1.yml's `name:` field) consistent.
