# vrec-models-v1 — 多模型聚合推理镜像

**状态**: 已批准，待实现
**日期**: 2026-06-18

## 1. 目标

提供单一 Docker 镜像，内置以下推理模型的代码与运行环境，权重运行时挂载：

- FoundationStereo
- Pi3
- vggt-omega
- sam3 / sam3.1（同一 repo）

镜像产出两种 tag：
- `ghcr.io/wangxinjian1108/vrec-models-v1:latest` — runtime，CMD = `bash`
- `ghcr.io/wangxinjian1108/vrec-models-v1:dev` — dev，FROM runtime，附 SSH + JupyterLab

## 2. 仓库布局

```
docker/
└── apps/
    └── vrec-models-v1/
        ├── Dockerfile          # runtime
        └── Dockerfile.dev      # dev (s6-overlay + SSH + JupyterLab)
.github/workflows/
└── docker-vrec-models-v1.yml
docs/superpowers/specs/
└── 2026-06-18-vrec-models-v1-design.md
```

`docker/apps/` 是新增子目录。约定：
- `docker/<repo-name>/` — 单 repo 镜像（现有 19 个）
- `docker/apps/<name>/` — 跨 repo 聚合应用镜像

## 3. Base 镜像

`nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04`

理由：4 个模型最高需 cu128 (sam3)；devel 镜像自带 nvcc + cuDNN headers，避免装额外 toolkit；PyTorch wheel 自带各自 CUDA runtime，跨 env 不冲突。

## 4. 镜像内部布局

| 路径 | 内容 |
|---|---|
| `/app/foundation_stereo` | `thirdparty/FoundationStereo` 代码 |
| `/app/pi3` | `thirdparty/Pi3` 代码 |
| `/app/vggt-omega` | `thirdparty/vggt-omega` 代码 |
| `/app/sam3` | `thirdparty/sam3` 代码（sam3 + sam3.1 共用） |
| `/opt/conda/envs/foundation_stereo` | python 3.11 + torch 2.4.1 cu124 + flash-attn |
| `/opt/conda/envs/pi3` | python 3.10 + torch 2.5.1 cu124 |
| `/opt/conda/envs/vggt-omega` | python 3.10 + torch 2.6.0 cu126 |
| `/opt/conda/envs/sam3` | python 3.12 + torch 2.10.0 cu128 + flash-attn-3 |
| `/opt/var/models/` | 空目录，运行时 `-v` 挂载权重 |

PyTorch wheel 自带 CUDA runtime，cu124/cu126/cu128 在 driver 12.8 上向下兼容。

env 切换：build 时执行 `conda init bash` 并把 `${CONDA_DIR}/bin` 加进 `PATH`（不把任何具体 env 的 bin 写进 PATH，避免默认绑定其中一个 env）。容器内启动 bash 后 `conda activate <env>` 切换。脚本场景用 `conda run -n <env> <cmd>`。

## 5. apt 包

复用 `dockerize-submodule.md` 模板的固定基础包，新增：

- `libarchive-tools`
- `netcat-openbsd`

并合并各子项目的图像/GUI 库需求：

- `libgl1`、`libglib2.0-0`（OpenCV / open3d，三个项目共用）
- `libsm6`、`libxext6`、`libxrender-dev`（vggt-omega）
- `libturbojpeg0-dev`（FoundationStereo）

`libarchive-tools` 和 `netcat-openbsd` 同时永久加入 `dockerize-submodule.md` 模板的固定列表（独立改动）。

## 6. 构建顺序

```dockerfile
FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04
ENV ...
WORKDIR /app

# apt + locale + miniconda + ssh-keygen (照搬现有模板)

# 一次性建 4 个空 env
RUN conda create -n foundation_stereo python=3.11 -y \
 && conda create -n pi3                python=3.10 -y \
 && conda create -n vggt-omega         python=3.10 -y \
 && conda create -n sam3               python=3.12 -y \
 && conda clean -afy

# 每个模型独立一个 RUN：COPY 源码 → 装 torch → 装 deps → 编扩展 → rm 多余
COPY thirdparty/FoundationStereo /app/foundation_stereo
RUN conda run -n foundation_stereo pip install torch==2.4.1 ... --index-url ...cu124 \
 && conda run -n foundation_stereo pip install <deps> \
 && conda run -n foundation_stereo pip install flash-attn --no-build-isolation

COPY thirdparty/Pi3 /app/pi3
RUN conda run -n pi3 pip install torch==2.5.1 ... --index-url ...cu124 \
 && conda run -n pi3 pip install -r /app/pi3/requirements.txt \
 && conda run -n pi3 pip install -e /app/pi3 \
 && rm -rf /app/pi3/assets

COPY thirdparty/vggt-omega /app/vggt-omega
RUN conda run -n vggt-omega pip install torch==2.6.0 ... --index-url ...cu126 \
 && conda run -n vggt-omega pip install -r /app/vggt-omega/requirements.txt \
 && conda run -n vggt-omega pip install -e /app/vggt-omega

COPY thirdparty/sam3 /app/sam3
RUN conda run -n sam3 pip install torch==2.10.0 torchvision --index-url ...cu128 \
 && conda run -n sam3 pip install -e "/app/sam3[notebooks]" \
 && conda run -n sam3 pip install einops ninja \
 && conda run -n sam3 pip install flash-attn-3 --no-deps --index-url ...cu128 \
 && rm -rf /app/sam3/examples /app/sam3/assets

CMD ["/bin/bash"]
```

每模型独立 RUN — 失败定位清楚，缓存粒度合适。

## 7. Dockerfile.dev

`FROM ${BASE_IMAGE:-ghcr.io/wangxinjian1108/vrec-models-v1:latest}`

完全套用现有 5 个 dev 镜像的 s6-overlay + SSH + JupyterLab + jovyan + root=`ShARC` 模板，无特殊化。

## 8. CI 工作流

`.github/workflows/docker-vrec-models-v1.yml`

照搬现有模板，差异：

- `paths` 触发：
  ```yaml
  - "docker/apps/vrec-models-v1/**"
  - "thirdparty/FoundationStereo"
  - "thirdparty/Pi3"
  - "thirdparty/vggt-omega"
  - "thirdparty/sam3"
  - ".github/workflows/docker-vrec-models-v1.yml"
  ```
- 不带 `HF_TOKEN` secret（不下权重）
- runtime tag: `latest`, `sha-xxx`；dev tag: `dev`, `dev-sha-xxx`

**风险**: 聚合镜像预估 ~25-30GB（4 套 conda env + flash-attn 编译产物）。GitHub-hosted runner 14GB RAM + ~25GB 可用磁盘可能不够，与现有大镜像（C4G ~30GB）一样会撞磁盘墙。

**第一次先用 GHA 试**。如果撞墙，回退方案：
1. 移除编译型扩展（flash-attn）改为运行时按需装
2. 切到 self-hosted runner
3. 本地构建 + push，仓库只保留 Dockerfile

## 9. 运行示例

```bash
# 拉镜像
docker pull ghcr.io/wangxinjian1108/vrec-models-v1:latest

# 跑 sam3 推理（权重挂载）
docker run --gpus all --rm -it \
  -v /path/to/weights:/opt/var/models \
  ghcr.io/wangxinjian1108/vrec-models-v1:latest \
  bash -lc "conda activate sam3 && python /app/sam3/scripts/demo.py ..."

# dev 镜像（SSH + Jupyter）
docker run --gpus all -d \
  -p 2222:22 -p 8888:8888 \
  -v /path/to/weights:/opt/var/models \
  ghcr.io/wangxinjian1108/vrec-models-v1:dev
```

## 10. 不在范围内

- 权重 bake（用户自己挂载或后续 push）
- 多模型协同入口脚本（CMD=bash，由用户自己组合）
- PPU 平台支持（前序对话已搁置）
- skill 抽象（待聚合镜像 ≥3 个时再抽 `dockerize-app` skill）

## 11. 验收标准

- `docker pull ghcr.io/wangxinjian1108/vrec-models-v1:latest` 成功
- 镜像内 `conda activate <env> && python -c "import torch; print(torch.cuda.is_available())"` 在四个 env 下都返回 True
- 挂载权重后能跑 sam3 / Pi3 / vggt-omega / FoundationStereo 各自的 demo 脚本（用户验证）
- `docker pull :dev` 后 SSH (`root:ShARC`) 与 JupyterLab (`:8888`) 可用
