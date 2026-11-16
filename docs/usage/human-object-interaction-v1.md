# human-object-interaction-v1 使用与推理指南

本文档对应当前带权重的 Zelos 内网镜像：

```text
repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest
```

镜像把 CHOIS、OMOMO、Kimodo、Blender 3.6.3 以及推理所需的预训练权重
打包在同一个环境中。权重已位于镜像内的 `/models`，默认配置为本地离线加载，
不需要启动 vLLM 或其他文本编码器 HTTP 服务。

## 1. 能力边界

| 模型 | 主要输入 | 主要输出 | 是否直接接受任意 GLB |
| --- | --- | --- | --- |
| CHOIS | 上游预处理后的物体/场景与人体条件数据，可选文本条件 | 人体与物体的交互动作、顶点/关节及可选渲染 | 否 |
| OMOMO | 上游 OMOMO 测试数据，两阶段人体操作动作条件 | 手部/脚部条件与全身动作、可选 Blender 可视化 | 否 |
| Kimodo | 文本提示，可选约束文件 | SOMA 人体动作 NPZ，可选 BVH | 不涉及物体输入 |

这份镜像提供模型的推理环境和权重。它不是“输入任意 GLB 后直接返回接触点”
的完整服务。若要做 GLB/VLM 接触点识别，还需要另外实现资产预处理、视角渲染、
关键点映射和结果可视化。

## 2. 镜像与权重

内网带权重镜像：

```text
repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest
```

镜像中的主要路径：

| 内容 | 镜像内路径 |
| --- | --- |
| CHOIS 源码 | `/app/chois_release` |
| OMOMO 源码 | `/app/omomo_release` |
| Kimodo 源码 | `/app/kimodo` |
| 全部预训练权重 | `/models` |
| CHOIS checkpoint | `/models/chois/model-10.pt` |
| OMOMO 标准版两阶段 checkpoint | `/models/omomo/stage1/model.pt`、`/models/omomo/stage2/model.pt` |
| OMOMO object-split 两阶段 checkpoint | `/models/omomo/stage1_object_split/model.pt`、`/models/omomo/stage2_object_split/model.pt` |
| Kimodo SOMA-RP v1.2 | `/models/kimodo/Kimodo-SOMA-RP-v1.2` |
| CLIP ViT-B/32 | `/models/clip/ViT-B-32.pt` |
| Llama 3 8B 与 LLM2Vec | `/models/text-encoders` |
| 逐文件 SHA256 清单 | `/models/weights-manifest.json` |

当前权重总量约 18 GB。`weights-manifest.json` 包含每个文件的大小和 SHA256，
可用于拷贝或迁移后的完整性检查。

### 镜像标签区别

- Zelos `:latest`：带完整权重，本文档使用这个标签。
- GHCR `human-object-interaction-v1:with-weights`：带完整权重。
- GHCR `human-object-interaction-v1:latest`：仅基础环境，不包含预训练权重。
- GHCR `human-object-interaction-v1-weights-chunks:latest`：只用于分块传输权重，
  不是推理环境。

## 3. 主机要求

推荐环境：

- Linux 主机。
- 已安装 Docker 和 NVIDIA Container Toolkit。
- NVIDIA 驱动能够运行 CUDA 12.x 容器。
- 至少 24 GB 显存；更高分辨率的渲染或更大的 batch 建议使用 32 GB 以上显存。
- 至少 32 GB 主机内存。
- 留出约 50 GB 空间用于拉取和解压镜像。

Kimodo 默认会把 8B LLM2Vec 文本编码器放在 GPU。显存紧张时，可以设置
`TEXT_ENCODER_DEVICE=cpu`，让文本编码器使用 CPU 和约 20–25 GB 主机内存，
动作扩散模型仍使用 GPU。

检查 NVIDIA 容器支持：

```bash
docker run --rm --gpus all \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  nvidia-smi
```

## 4. 拉取镜像

如果 registry 需要登录，先执行：

```bash
docker login repo-volc.zelostech.com.cn
```

然后拉取：

```bash
docker pull \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest
```

可以选择设置本地短标签：

```bash
docker tag \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  hoi-v1:latest
```

后续示例使用完整内网镜像名，便于直接复制运行。

## 5. 离线自检

下面的检查完全在 CPU 上运行，并禁用容器网络。它会验证权重结构、本地 CLIP、
Kimodo 模型、Llama 分片、tokenizer、LLM2Vec 适配器、CLI 和 Blender：

```bash
docker run --rm --network none \
  -e NVIDIA_VISIBLE_DEVICES=none \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  human-object-interaction-smoke-test
```

成功时最后一行类似：

```text
HOI weighted image: checkpoint loads and local CLIP passed; GPU end-to-end inference is a separate check
```

### 5.1 Kimodo GPU 快速验证

下面是一条已实际验证可运行的完整离线推理命令。它先生成 1 秒动作，只执行
2 步扩散，并用 CPU 加载文本编码器，适合确认 GPU、文本编码器和输出挂载都正常：

```bash
mkdir -p /tmp/hoi-kimodo-smoke

docker run --rm --network none --gpus all --shm-size=16g \
  -e TEXT_ENCODER_DEVICE=cpu \
  -v /tmp/hoi-kimodo-smoke:/outputs \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  kimodo-gen 'A person pushes a luggage case.' \
  --duration 1 \
  --num_samples 1 \
  --diffusion_steps 2 \
  --no-postprocess \
  --output /outputs/test \
  --seed 42
```

成功后应生成：

```text
/tmp/hoi-kimodo-smoke/test.npz
```

## 6. 宿主机目录和挂载

建议把输入和输出放在固定目录，例如：

```text
/data/hoi/
├── chois/
│   └── processed_data/
├── omomo/
│   └── data/
├── smplh_amass/
│   └── male/
│       └── model.npz
└── outputs/
```

创建输出目录：

```bash
mkdir -p /data/hoi/outputs
```

通用启动模板：

```bash
docker run --rm --gpus all --shm-size=16g \
  -v /data/hoi:/data/hoi \
  -v /data/hoi/outputs:/outputs \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  <container-command>
```

不要把空的宿主目录直接挂到 `/models`：

```bash
# 错误示例：会遮住镜像内置的全部权重
-v /empty/path:/models
```

如需额外挂载 SMPL-H，只挂载它的子目录：

```bash
-v /data/hoi/smplh_amass:/models/smplh_amass:ro
```

## 7. Kimodo：文本生成人体动作

Kimodo 是三个模型中唯一可以直接用文本快速验证的入口。镜像默认使用：

```text
Kimodo-SOMA-RP-v1.2
```

并自动从 `/models/kimodo` 和 `/models/text-encoders` 加载本地模型。

### 7.1 基本文本推理

```bash
mkdir -p "$PWD/outputs"

docker run --rm --gpus all --shm-size=16g \
  -v "$PWD/outputs:/outputs" \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  kimodo-gen 'A person walks forward and pushes a suitcase.' \
  --duration 5 \
  --num_samples 1 \
  --output /outputs/kimodo/push_suitcase \
  --seed 42
```

默认输出：

```text
outputs/kimodo/push_suitcase.npz
```

NPZ 的主要字段：

| 字段 | 形状 | 含义 |
| --- | --- | --- |
| `posed_joints` | `(T, 77, 3)` | SOMA 77 关节的全局坐标 |
| `posed_joints_norootpos` | `(T, 30, 3)` | 去掉根节点位移后的 30 关节坐标 |
| `root_positions` | `(T, 3)` | 根节点位置 |
| `smooth_root_pos` | `(T, 3)` | 后处理后的根节点位置 |
| `global_rot_mats` | `(T, 77, 3, 3)` | 全局旋转矩阵 |
| `local_rot_mats` | `(T, 77, 3, 3)` | 局部旋转矩阵 |
| `global_root_heading` | `(T, 2)` | 根节点朝向 |
| `foot_contacts` | `(T, 6)` | 左右脚接触状态 |

需要 BVH 时增加：

```bash
--bvh
```

生成的 BVH 与 NPZ 使用相同输出前缀。SOMA 模型还可以使用
`--bvh_standard_tpose` 导出标准 T-pose。

### 7.2 显存不足时

将 8B 文本编码器放到 CPU：

```bash
docker run --rm --gpus all --shm-size=16g \
  -e TEXT_ENCODER_DEVICE=cpu \
  -v "$PWD/outputs:/outputs" \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  kimodo-gen 'A person pulls a suitcase with the right hand.' \
  --duration 3 \
  --num_samples 1 \
  --output /outputs/kimodo/pull_suitcase \
  --seed 42
```

这种方式会用更多主机内存，但显著降低 8B 编码器占用的显存。

### 7.3 多段动作与常用参数

多个提示可以用句号分隔：

```bash
kimodo-gen \
  'A person walks toward a suitcase. The person pushes the suitcase forward.' \
  --duration '3 4' \
  --num_samples 1 \
  --num_transition_frames 10 \
  --output /outputs/kimodo/multi_step \
  --seed 42
```

常用参数：

- `--duration`：生成秒数；多段提示可传空格分隔的多个时长。
- `--num_samples`：每段提示生成数量。
- `--diffusion_steps`：扩散步数，默认通常为 100；快速调试可临时设成 2。
- `--num_transition_frames`：多段动作之间的过渡帧数。
- `--seed`：固定随机种子，便于复现。
- `--save_example_dir`：额外保存 demo 兼容目录。
- `--constraints`：加载已有约束列表。
- `--input_folder`：从包含 `meta.json` 和可选 `constraints.json` 的目录读取输入。
- `--bvh`、`--bvh_standard_tpose`：额外导出 BVH。

查看当前镜像中的完整参数：

```bash
docker run --rm \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  kimodo-gen --help
```

## 8. CHOIS 推理

CHOIS 入口是：

```bash
chois-infer
```

脚本已经自动加入官方 checkpoint、文本条件、对象关键点、语义接触、
随机 BPS、第一帧人体姿态和 guidance 等参数。用户通常只需要提供数据和输出路径。

### 8.1 必要数据

CHOIS 需要上游预处理数据，而不是单张图片或单个 GLB。默认应挂载到：

```text
/app/chois_release/processed_data
```

其中还需要上游要求的：

- 人体资源：`smpl_all_models/smplx/SMPLX_MALE.npz`、
  `smpl_all_models/smplx/SMPLX_FEMALE.npz`。
- CHOIS 对应的物体、场景、运动或条件数据。
- 需要渲染视频时，上游布局中的 `blender_files` 场景。
- `SMPLH_PATH=/models/smplh_amass` 指向的 `male/model.npz`。

人体模型需要从官方许可渠道自行准备，镜像不包含 SMPL-H/SMPL-X 文件。
数据构建方法见
[CHOIS 上游 README](../../thirdparty/chois_release/README.md)。

### 8.2 单窗口推理

```bash
docker run --rm --gpus all --shm-size=16g \
  -v /data/hoi/chois:/data/chois \
  -v /data/hoi/smplh_amass:/models/smplh_amass:ro \
  -v /data/hoi/outputs:/outputs \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  chois-infer \
  --batch_size=1 \
  --data_root_folder=/data/chois/processed_data \
  --save_res_folder=/outputs/chois \
  --device=0
```

入口已经等价于包含以下关键官方参数：

```text
--test_sample_res
--window=120
--pretrained_model=/models/chois/model-10.pt
--input_first_human_pose
--use_random_frame_bps
--add_language_condition
--use_object_keypoints
--add_semantic_contact_labels
--use_guidance_in_denoising
```

如果数据是按 object-split 测试集组织的，可以额外传：

```bash
--use_object_split
```

需要定量评估时增加：

```bash
--for_quant_eval
```

不启用可视化可以减少对 `.blend` 场景和 Blender 渲染资源的依赖。

查看完整参数：

```bash
docker run --rm \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  chois-infer --help
```

## 9. OMOMO 推理

OMOMO 入口是：

```bash
omomo-infer
```

脚本默认执行两阶段完整 pipeline：

1. 第一阶段生成手部/脚部操作条件。
2. 第二阶段根据条件生成全身动作。

默认 checkpoint 为：

```text
/models/omomo/stage1/model.pt
/models/omomo/stage2/model.pt
```

### 9.1 必要数据

OMOMO 测试数据默认应位于：

```text
/app/omomo_release/data
```

还需要：

- `data/smpl_all_models/smplx/SMPLX_MALE.npz`。
- `data/smpl_all_models/smplx/SMPLX_FEMALE.npz`。
- `/models/smplh_amass/male/model.npz`。
- 开启可视化时，默认读取
  `data/blender_files/floor_colorful_mat.blend`。

可以通过环境变量覆盖 Blender 场景：

```bash
-e OMOMO_BLENDER_SCENE=/data/omomo/blender_files/custom.blend
```

数据和可视化说明见
[OMOMO 上游 README](../../thirdparty/omomo_release/README.md)。

### 9.2 标准两阶段推理

```bash
docker run --rm --gpus all --shm-size=16g \
  -v /data/hoi/omomo:/data/omomo \
  -v /data/hoi/smplh_amass:/models/smplh_amass:ro \
  -v /data/hoi/outputs:/outputs \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  omomo-infer \
  --batch_size=1 \
  --data_root_folder=/data/omomo/data \
  --project=/outputs/omomo \
  --exp_name=stage1 \
  --fullbody_exp_name=stage2 \
  --for_quant_eval \
  --device=0
```

`--for_quant_eval` 适合只检查数值结果。去掉它后，上游入口会尝试生成
Blender 可视化，因此必须准备可用的 `.blend` 场景。

### 9.3 OMOMO object-split

```bash
docker run --rm --gpus all --shm-size=16g \
  -v /data/hoi/omomo:/data/omomo \
  -v /data/hoi/smplh_amass:/models/smplh_amass:ro \
  -v /data/hoi/outputs:/outputs \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  omomo-infer \
  --batch_size=1 \
  --data_root_folder=/data/omomo/data \
  --project=/outputs/omomo-object-split \
  --exp_name=stage1 \
  --fullbody_exp_name=stage2 \
  --checkpoint=/models/omomo/stage1_object_split/model.pt \
  --fullbody_checkpoint=/models/omomo/stage2_object_split/model.pt \
  --use_object_split \
  --for_quant_eval \
  --device=0
```

查看完整参数：

```bash
docker run --rm \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  omomo-infer --help
```

## 10. 进入容器调试

需要反复运行命令时，可以启动交互式容器：

```bash
docker run --rm -it --gpus all --shm-size=16g \
  -v /data/hoi:/data/hoi \
  -v /data/hoi/outputs:/outputs \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  bash
```

容器内常用命令：

```bash
chois-infer --help
omomo-infer --help
kimodo-gen --help

conda env list
conda run -n hoi python -c 'import torch; print(torch.__version__)'
conda run -n kimodo python -c 'import torch; print(torch.__version__)'

blender --version
nvidia-smi
```

两个 Conda 环境：

- `hoi`：CHOIS 和 OMOMO，Python 3.8、PyTorch 1.11。
- `kimodo`：Kimodo，Python 3.10、PyTorch 2.5.1。

自定义脚本应通过对应的 `conda run -n <env>` 调用，避免混用两个环境。

## 11. 关键环境变量

镜像已经设置：

```text
SMPLH_PATH=/models/smplh_amass
BLENDER_PATH=/usr/local/bin/blender
CHECKPOINT_DIR=/models/kimodo
TEXT_ENCODERS_DIR=/models/text-encoders
TEXT_ENCODER_MODE=local
LOCAL_CACHE=True
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
CLIP_MODEL_PATH=/models/clip/ViT-B-32.pt
CLIP_DOWNLOAD_ROOT=/models/clip
```

常用运行时覆盖：

```bash
-e TEXT_ENCODER_DEVICE=cpu
-e OMOMO_BLENDER_SCENE=/data/omomo/custom.blend
```

## 12. 导出镜像内权重

如果还需要在宿主机保留一份权重：

```bash
docker create \
  --name hoi-weight-export \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest

mkdir -p /data/hoi/exported-models
docker cp hoi-weight-export:/models/. /data/hoi/exported-models/
docker rm hoi-weight-export
```

导出后可以对照 `exported-models/weights-manifest.json` 校验文件。

## 13. 常见问题

### `CUDA out of memory`

先使用 `--batch_size=1`，停止宿主机上占用 GPU 的无关进程。Kimodo 可增加：

```bash
-e TEXT_ENCODER_DEVICE=cpu
```

### Kimodo 看起来停在文本编码阶段

8B 文本编码器首次加载需要较多时间，CPU 模式尤其如此。检查：

```bash
docker stats
nvidia-smi
```

CPU 文本编码器通常占用约 20–25 GB 内存，属于正常现象。

### 找不到 SMPL/SMPLX 文件

确认实际路径为：

```text
/models/smplh_amass/male/model.npz
/data/chois/processed_data/smpl_all_models/smplx/SMPLX_MALE.npz
/data/chois/processed_data/smpl_all_models/smplx/SMPLX_FEMALE.npz
/data/omomo/data/smpl_all_models/smplx/SMPLX_MALE.npz
/data/omomo/data/smpl_all_models/smplx/SMPLX_FEMALE.npz
```

### 权重突然全部找不到

检查是否把空目录挂载到了 `/models`。应只挂载 `/models/smplh_amass` 等子目录。

### CHOIS/OMOMO 可视化失败

先加 `--for_quant_eval` 验证数值推理。可视化还要求对应的
`blender_files` 场景、Blender 可执行文件和可写的输出目录。

### 误在训练环境运行

`chois-infer` 和 `omomo-infer` 已经设置了推理模式。直接调用上游 Python
入口时如果没有带 `--test_sample_res` 或 `--run_whole_pipeline`，程序会进入训练流程。
优先使用镜像提供的三个 wrapper 命令。

### 容器没有网络但程序仍尝试下载模型

镜像默认启用 HF/Transformers 离线模式，并从 `/models` 加载权重。
出现下载请求通常说明挂载覆盖了内置权重，或手动改错了 checkpoint、
text encoder 路径。

## 14. 快速选择

- 只想验证文本动作生成：运行 Kimodo。
- 已有 CHOIS 官方预处理数据：运行 `chois-infer`。
- 已有 OMOMO 官方测试数据：运行 `omomo-infer`。
- 只有 GLB、没有模型专用预处理数据：先按各上游仓库的数据要求完成预处理；
  当前 wrapper 不能直接接收单个 GLB。
