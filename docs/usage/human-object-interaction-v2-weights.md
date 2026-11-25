# Human Object Interaction V2：含权重内网版

该版本基于 GitHub Actions 构建的 V2 环境，在本机添加公开预训练权重。
基础环境摘要为：

```text
ghcr.io/wangxinjian1108/human-object-interaction-v2@sha256:89aa3801e1bdcd7499a8a03a9863bc84474fcacd51929da4b17e54d8b1c870c1
```

内网目标：

```text
repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v2:latest
```

权重清单在 `/models/weights-manifest-v2.json`，包含来源、固定版本、文件大小和
SHA256；下载和验证脚本位于仓库 `docker/apps/human-object-interaction-v2-weights/`。
已发布的固定版本和摘要：

```text
repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v2:weights-20261125
repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v2@sha256:f4462909a9c913c2006a279f30cefbd306f411fc2ca06e4ef974631e20e4247f
```

`latest` 与上述固定标签指向同一摘要。镜像包含 49 层，压缩层合计约
**113.83 GiB**，展开约 **179.36 GiB**；拉取时需要额外临时空间。

## 内容与目录

| 模型／组件 | 权重目录 | 运行环境 |
|---|---|---|
| CHOIS | `/models/chois/model-10.pt` | `/opt/conda/envs/hoi` |
| OMOMO | `/models/omomo/{stage1,stage2,stage1_object_split,stage2_object_split}/model.pt` | `/opt/conda/envs/hoi` |
| Kimodo SOMA RP v1.2 | `/models/kimodo/Kimodo-SOMA-RP-v1.2` | `/opt/conda/envs/kimodo` |
| Kimodo Llama 3 8B 与两个 LLM2Vec adapter | `/models/text-encoders` | 同上 |
| LIGHT 三个数据集的 checkpoint、evaluator | `/models/light`；链接到 `/app/LIGHT/save` 和 `/app/LIGHT/assets/evaluator.ckpt` | `/opt/conda/envs/light` |
| InterAct 生成模型、evaluator／text encoder | `/models/interact`；链接到 `/app/InterAct/text2interaction/save` 和 `assets/eval/markersbps.ckpt` | `/opt/conda/envs/interact` |
| HAIC 7 个公开 MuJoCo ONNX 策略 | `/models/haic/haic` | 参照下方限制 |
| GRAIL GEM-X、SOMA-X、人体检测与姿态权重 | `/models/grail/gem-x`；链接到 GEM-X 和 GRAIL cache | `/root/.cache/grail/envs/gem-x` |
| GRAIL MoSE3、FoundationPose、SONIC | `/models/grail/{MoSE3,FoundationPose,SONIC}`；链接到对应 `imports` 目录 | GRAIL／SONIC 环境 |
| GRAIL MoGe-3、SAM2 | `/models/grail/{moge3,sam2}`；提供 HF 离线缓存 | GRAIL／MoGe 环境 |
| GRAIL 可选 Hunyuan3D 2.1 shape、VAE、paint、DINOv2 large／giant、RealESRGAN | `/models/grail`；提供 Hunyuan 与 HF 离线路径 | `/root/miniconda3/envs/hunyuan` |
| DistilBERT、CLIP | `/models/grail/distilbert`、`/models/clip` | 对应模型环境 |

不提供训练／评测数据集。SMPL-H、SMPL-X、DMPL 需要用户准备相应人体模型文件。
LIGHT 与 InterAct 的完整推理还会读取这些人体模型和数据统计量；仅有生成网络权重
不能替代这些输入。

HAIC 权重来自上游关联的 `Cybercal/HOIC-baseline`，用于 MuJoCo 部署，包含箱子、
地形箱子、拉车、带箱子的拉车、推车、推轮椅和滑板任务。这些 ONNX 文件不能直接
传给 `/app/HAIC/scripts/play.py` 的 `checkpoint_path`；后者仍需要任务匹配的
Isaac Sim PyTorch checkpoint。镜像包含 HAIC 的原有推理环境，未将另一个仓库的
MuJoCo 部署程序替换进 HAIC。

GRAIL 的独立 MiniMax-H3／外部视频生成服务不属于此权重包。需要该服务的流程
应按 GRAIL 上游配置服务地址或提供已生成的视频。本镜像的权重包不代表所有可选
外部服务和完整仿真均可离线运行。

## 启动

```bash
IMAGE=repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v2:latest
docker pull "$IMAGE"
docker run --rm -it --gpus all --network none --shm-size=16g \
  -v /data/hoi-input:/inputs:ro \
  -v /data/hoi-output:/outputs \
  "$IMAGE" bash
```

不要把空目录挂载到整个 `/models`、`/root/.cache` 或 `/workspace/grail`：这些目录
包含已打包权重、环境或源码。需要添加人体模型时，挂载具体路径，例如：

```bash
-v /data/body-models:/app/LIGHT/models:ro \
-v /data/body-models:/app/InterAct/models:ro \
-v /data/smplh_amass:/models/smplh_amass:ro
```

本机 NVIDIA L4 驱动为 550.144.03，镜像继承的启动条件为 `cuda>=12.8`。
之前的基础 CUDA 检查使用额外参数 `-e NVIDIA_DISABLE_REQUIRE=1` 绕过该启动条件。
这只绕过容器运行时检查；完整 GRAIL／Isaac Sim 仿真仍需满足各自驱动和显存要求。
CPU 文件检查可使用 `--runtime runc`，不加 `--gpus all`。

## 入口示例

CHOIS、OMOMO、Kimodo 分别通过 `chois-infer`、`omomo-infer`、`kimodo-gen` 进入。
数据准备和参数格式见 [V1 使用说明](human-object-interaction-v1.md)，环境与仿真入口
见 [V2 环境说明](human-object-interaction-v2.md)。

LIGHT 使用上游脚本，其模型目录已对应到公开 checkpoint：

```bash
cd /app/LIGHT
conda run --no-capture-output -n light bash scripts/generate.sh --dataset omomo
# 或 --dataset behave / --dataset interact
```

InterAct 使用：

```bash
cd /app/InterAct/text2interaction
conda run --no-capture-output -n interact bash scripts/run_sample_nonguide.sh
```

这些入口需要先按上游说明准备人体模型、物体资产、数据和归一化统计量。
`--network none` 可以检查是否还有未准备的外部依赖；它不会补齐缺少的输入。

镜像中的 HF 及 Transformers 默认离线，Kimodo 文本编码器走本地文件。
权重文件检查与真实数据上的生成、渲染和仿真是不同的验证范围。

## 本次验证范围

最终镜像展开约 **179.36 GiB**，权重及配置清单共 **140 个文件、60.89 GiB**。
继承和新增文件已核对哈希，checkpoint 压缩包的解压文件另核对 ZIP CRC；
生成的 GEM-X 运行配置也记录了 SHA256。镜像启动默认仍为 `bash`。

| 检查 | 结果 |
|---|---|
| HF 离线缓存 | 65 个资源在 `--network none` 容器内由 `local_files_only=True` 定位成功 |
| LIGHT | 3 个真实 checkpoint 加本地 DistilBERT，均通过 4 帧合成输入的 CPU 去噪网络前向 |
| InterAct | 真实生成网络、evaluator 文本编码器加载成功；本地 DistilBERT 文本前向输出 `(1, 256)`，全程断网 |
| HAIC | 7 个 ONNX 策略在 CPU 上通过合成输入前向，输出均为有限值 |
| 最终镜像 | 无宿主权重挂载时，文件清单、离线环境变量、Hunyuan 路径及默认 shell 启动检查通过 |

InterAct 上游构造函数加载 evaluator 时未指定 `map_location`，因此上述加载检查
使用 GPU 可见容器；这不等于完整 PointNet2 采样或动作生成检查。GRAIL 本次验证
了权重完整性和缓存路径，尚未运行完整重建／追踪／仿真。CHOIS、OMOMO 之前的
采样验证及限制见 [验证记录](human-object-interaction-validation.md)。

需要重新核对所有权重时，可在镜像中运行 `hoi-weights-verify`。这会读取约 60 GiB
文件，不适合作为频繁调用的健康检查。对应组件检查脚本保存在
`/opt/hoi-weights-v2/tests/`。
