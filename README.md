# VRecHub

3D 重建 / 视觉几何 / 建图相关开源模型的容器化中心。每个 model 以 submodule 形式接入 `thirdparty/`，自动生成 runtime + dev 双镜像并推到 GHCR / Docker Hub。所有镜像目录见 [IMAGES.md](IMAGES.md)。

镜像分两类：
- **Runtime 镜像** `ghcr.io/wangxinjian1108/<name>:latest` — 烧好 conda env、依赖、模型权重，能直接跑 inference。
- **Dev 镜像** `ghcr.io/wangxinjian1108/<name>:dev` — 在 runtime 上加 JupyterLab + sshd（s6 管），用于 K8s Notebook 部署。

## Skills 速查表

仓库带了一组工程化 skill，覆盖从添加 repo、构建镜像、到验证、审查、通知的全流程。Claude 用 `/skill-name` 触发；codex/openai 用 `$skill-name` 触发。

| Skill | 作用 | Claude | Codex |
|---|---|:---:|:---:|
| [`add-repo`](codex-skills/add-repo/SKILL.md) | 给一个 git URL，全自动接入：加 submodule → 生成 Dockerfile + Dockerfile.dev → 生成 workflow → 刷新 IMAGES.md → commit + push + 看 CI | ✅ | ✅ |
| [`dockerize-submodule`](codex-skills/dockerize-submodule/SKILL.md) | 给一个已存在的 submodule，生成 runtime Dockerfile + workflow（自动识别 CUDA / Python / PyTorch / 系统依赖） | ✅ | ✅ |
| [`dev-image`](codex-skills/dev-image/SKILL.md) | 给一个 model name，在 runtime 之上派生 dev 镜像（s6 + sshd + JupyterLab + NB_PREFIX），并把 dev build 串进同一个 workflow | — | ✅ |
| [`list-images`](codex-skills/list-images/SKILL.md) | 扫所有 `docker-*.yml` 和 submodule README，重写 [`IMAGES.md`](IMAGES.md) | ✅ | ✅ |
| [`update-submodule`](codex-skills/update-submodule/SKILL.md) | 把指定 submodule 更新到 upstream 最新 commit，提交 pointer 改动，触发镜像重建 | ✅ | ✅ |
| [`train-test`](codex-skills/train-test/SKILL.md) | 拉镜像，在 submodule dev 分支上做数据集转换，跑一个 epoch 训练验证整条 pipeline 通 | ✅ | ✅ |
| [`ship`](codex-skills/ship/SKILL.md) | 把当前未提交的改动 commit + push，必要时开 PR，监控 CI 最多 3 轮修复 | ✅ | ✅ |
| [`review`](codex-skills/review/SKILL.md) | 用挑刺心态审 PR / diff，重点找正确性 / 回归 / 错误假设 / 缺测试 | — | ✅ |
| [`security-review`](codex-skills/security-review/SKILL.md) | 审 diff 的安全问题：secret 泄漏、供应链、Dockerfile / CI 权限 | — | ✅ |
| [`simplify`](codex-skills/simplify/SKILL.md) | 不改行为前提下简化代码 / 脚本 / Dockerfile，去重 + 降复杂度 | — | ✅ |
| [`notify`](codex-skills/notify/SKILL.md) | 把 commit / CI 状态推到 Slack `#cc` 等渠道 | — | ✅ |

> Claude 列有 ✅ 表示 `.claude/commands/` 下也有对应的 markdown command；codex 列总是 ✅，因为这些 skill 主要在 codex-skills/ 下维护。

## 最常用的几条工作流

### 新增一个 model

```
/add-repo git@github.com:org/repo-name.git
```

自动跑完整条 onboarding pipeline，结束时 master 上多出：`thirdparty/<repo-name>` submodule、`docker/<repo-name>/Dockerfile{,.dev}`、`.github/workflows/docker-<repo-name>.yml`、`IMAGES.md` 里多一行。

### 给已有 submodule 补镜像

```
/dockerize-submodule thirdparty/Scal3R     # 只产 runtime
/dev-image Scal3R                           # 在 runtime 上加 dev 镜像
```

### 提交本地改动

```
/ship                          # 自动从 diff 生成 commit message
/ship "fix: tweak xxx"         # 指定 commit message
```

`ship` 会自动判断是否要开 PR，并监控 CI 最多 3 轮自动修复。

### 更新某个 model 到 upstream 最新

```
/update-submodule vggt-omega
```

### 重新生成镜像目录

```
/list-images
```

会扫所有 workflow + Dockerfile + README，刷新 [IMAGES.md](IMAGES.md)。

## CI 镜像构建管线

每个 model 的 `docker-<name>.yml` workflow 在以下情况触发：
- push 到 `master` 且 paths 命中 `docker/<name>/**`、`thirdparty/<name>`、workflow 文件本身
- 打 `v*.*.*` tag
- 对 master 的 PR（runtime 验证 build，dev 跳过）
- 手动 `workflow_dispatch`

**双镜像构建模式**（vggt-omega 验证过的设计）：
1. Runtime build 用 `docker/build-push-action@v6` 的 `push: true` 直接流式推 GHCR，**不**用 `load: true`（大镜像会爆 runner 磁盘）
2. Dev build 用 `--build-arg BASE_IMAGE=ghcr.io/.../<name>:sha-<short>` 从刚 push 的 runtime sha tag 按需拉 layers，加上 s6/sshd/jupyter 层后推 `:dev`
3. PR 上 dev 跳过（没有已 push 的 runtime 可拉）

详见 [`codex-skills/add-repo/SKILL.md`](codex-skills/add-repo/SKILL.md) 的 *Dockerization requirements* 段。

## 仓库 Secrets 配置

在 Settings → Secrets and variables → Actions 加入：

| Secret | 用途 |
|---|---|
| `DOCKERHUB_USERNAME` | Docker Hub 用户名（不设则跳过 Docker Hub 推送，仅推 GHCR） |
| `DOCKERHUB_TOKEN` | Docker Hub Access Token |
| `HF_TOKEN` | HuggingFace token，仅用于私有 / gated 模型的 `--mount=type=secret,id=hf_token` 下载 |
| `HARBOR_USERNAME` / `HARBOR_PASSWORD` | 可选，推 Zelos 内部 Harbor（多数 model 不开） |

`GITHUB_TOKEN` 由 GitHub 自动注入，无需配置。

## 仓库结构

```
.github/workflows/    # 每个 model 一个 docker-<name>.yml
.claude/commands/     # Claude 版的 slash command（.md）
codex-skills/         # Codex / OpenAI 版 skill 定义（每个一个目录）
docker/               # 每个 model 一个子目录 + Dockerfile + Dockerfile.dev；docker/Dockerfile{,.dev} 是模板
thirdparty/           # 所有 model 的 git submodule
IMAGES.md             # 镜像与论文索引（list-images skill 生成）
```
