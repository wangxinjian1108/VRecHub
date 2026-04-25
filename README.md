# VRecHub

## Claude Skills

### `/dockerize-submodule`

为指定的 submodule 自动生成 Dockerfile 和 GitHub Actions 构建 workflow。

**用法**

```
/dockerize-submodule <submodule路径或名称>
```

示例：

```
/dockerize-submodule thirdparty/Scal3R
/dockerize-submodule Scal3R
```

**生成的文件**

| 文件 | 说明 |
|------|------|
| `docker/<repo-name>/Dockerfile` | 最小可运行的镜像构建文件 |
| `.github/workflows/docker-<repo-name>.yml` | 推送到 Docker Hub 和 ghcr.io 的 CI workflow |

**Dockerfile 行为**

- 自动检测项目类型（Python / Node / Go 等）并选择合适的 base image
- 依赖 submodule 从 build context（仓库根目录）本地 COPY，不走网络
- 安装完依赖后在同一层删除源码目录，保持镜像干净
- 包含 HuggingFace 模型下载的注释模板，取消注释并填入 model ID 即可使用

**模型下载模板**

生成的 Dockerfile 中会包含以下注释块，按需取消注释：

```dockerfile
# --- HuggingFace model download ---
# 公开模型：
# RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('org/model-name', local_dir='/models/model-name')"
# 私有模型（token 通过 BuildKit secret 注入，不会写入镜像层）：
# RUN --mount=type=secret,id=hf_token \
#     HF_TOKEN=$(cat /run/secrets/hf_token) python -c \
#     "from huggingface_hub import snapshot_download; snapshot_download('org/model-name', local_dir='/models/model-name', token=open('/run/secrets/hf_token').read().strip())"
# ----------------------------------
```

**GitHub Actions workflow 行为**

- push 到 `master` → 构建并推送，打 `latest` tag
- 打 `v*.*.*` tag → 推送带版本号的镜像（如 `1.2.3`、`1.2`）
- PR → 只构建不推送
- 支持手动触发（workflow_dispatch）

**前置配置**

在仓库 Settings → Secrets and variables → Actions 中添加：

| Secret | 说明 |
|--------|------|
| `DOCKERHUB_USERNAME` | Docker Hub 用户名 |
| `DOCKERHUB_TOKEN` | Docker Hub Access Token |
| `HF_TOKEN` | HuggingFace token（仅私有模型需要） |

`GITHUB_TOKEN` 由 GitHub 自动提供，无需手动配置。
