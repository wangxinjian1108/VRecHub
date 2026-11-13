# human-object-interaction-v1

CHOIS、OMOMO 和 Kimodo 的聚合推理环境，通过
`.github/workflows/docker-human-object-interaction-v1.yml` 在 GitHub Actions 构建并发布：

```text
ghcr.io/wangxinjian1108/human-object-interaction-v1:latest
```

| 模型 | 源码路径 | Conda 环境 | Python | PyTorch / CUDA runtime |
| --- | --- | --- | --- | --- |
| CHOIS | `/app/chois_release` | `hoi` | 3.8 | 1.11.0 / 11.3 |
| OMOMO（两阶段） | `/app/omomo_release` | `hoi` | 3.8 | 1.11.0 / 11.3 |
| Kimodo | `/app/kimodo` | `kimodo` | 3.10 | 2.5.1 / 12.4 |

CHOIS 与 OMOMO 的上游依赖清单一致，共享 `hoi` 环境，保留官方 PyTorch 版本和
PyTorch3D 0.7.2 二进制包。Kimodo 使用独立环境。系统 CUDA SDK 为 12.8，
两套 PyTorch wheel 分别自带运行库；运行需要支持这些运行库的宿主机 NVIDIA 驱动。
镜像还包含 Blender 3.6.3、FFmpeg 和常用开发工具。

## 不包含权重

不下载或打包 CHOIS、OMOMO、Kimodo、CLIP 的预训练权重，也不包含 SMPL 人体参数
或数据集。保留上游 `chois_release/bps.pt`，它是 13 KB 的固定随机采样点集合，
是 BPS 输入几何，不是训练权重。OMOMO 首次运行会按上游逻辑生成其 BPS 点集合。

CHOIS/OMOMO 需要上游提供的预处理数据和人体模型；这份镜像提供它们原有的推理入口，
尚未把它们改造为直接输入任意 GLB 的服务。

## 启动及检查

在宿主机准备 `/data/hoi/models`、`/data/hoi/chois/processed_data`、
`/data/hoi/omomo/data` 和 `/data/hoi/outputs`，再运行：

```bash
docker run --rm -it --gpus all --shm-size=16g \
  -v /data/hoi/models:/models \
  -v /data/hoi/chois/processed_data:/app/chois_release/processed_data \
  -v /data/hoi/omomo/data:/app/omomo_release/data \
  -v /data/hoi/outputs:/outputs \
  ghcr.io/wangxinjian1108/human-object-interaction-v1:latest

# 在容器中查看实际 CLI 参数：
chois-infer --help
omomo-infer --help
kimodo-gen --help

# 无 GPU、无权重依赖检查；运行时需保持 /models 不含权重才能通过权重扫描：
human-object-interaction-smoke-test
```

源码中的机器特定路径只在镜像内修正，不修改两个上游子模块。入口脚本切换到各自目录，
避免两个项目同名的 `manip` 包相互干扰。

## 挂载资源和运行

- CHOIS 权重示例：`/models/chois/model-10.pt`。
- OMOMO 两阶段权重示例：`/models/omomo/stage1.pt`、`/models/omomo/stage2.pt`。
- 两个数据根目录各自需要 `smpl_all_models/smplx/SMPLX_MALE.npz` 和
  `smpl_all_models/smplx/SMPLX_FEMALE.npz`，以及上游对应的预处理数据。
- 运动学树使用 `SMPLH_PATH=/models/smplh_amass`，需要该目录下的 `male/model.npz`。
- CHOIS 文本条件依赖 CLIP。离线运行时设置 `CLIP_MODEL_PATH` 为已有 CLIP 权重文件的
  容器内绝对路径；也可以把对应文件放到默认缓存 `/models/clip`。
- Kimodo 缓存默认 `HF_HOME=/models/huggingface`。完全离线时预先准备模型及文本编码器，
  并按其 CLI 指定路径；可设置 `HF_HUB_OFFLINE=1`。
- CHOIS 渲染场景按上游布局放到 `processed_data/blender_files/`。OMOMO 默认读取
  `data/blender_files/floor_colorful_mat.blend`，可用 `OMOMO_BLENDER_SCENE` 覆盖。

CHOIS 单窗口推理（容器内）：

```bash
export CLIP_MODEL_PATH=/models/clip/ViT-B-32.pt
chois-infer \
  --window=120 --batch_size=1 \
  --data_root_folder=/app/chois_release/processed_data \
  --pretrained_model=/models/chois/model-10.pt \
  --save_res_folder=/outputs/chois \
  --input_first_human_pose --use_random_frame_bps --add_language_condition \
  --use_object_keypoints --add_semantic_contact_labels \
  --loss_w_feet=1 --loss_w_fk=0.5 --loss_w_obj_pts=1 \
  --use_guidance_in_denoising
```

OMOMO 完整两阶段推理：

```bash
omomo-infer \
  --window=120 --batch_size=1 \
  --data_root_folder=/app/omomo_release/data \
  --checkpoint=/models/omomo/stage1.pt \
  --fullbody_checkpoint=/models/omomo/stage2.pt \
  --project=/outputs/omomo --exp_name=stage1 --fullbody_exp_name=stage2 \
  --for_quant_eval
```

`chois-infer` 默认加入 `--test_sample_res`，`omomo-infer` 默认加入
`--run_whole_pipeline`。省去 OMOMO 示例中的 `--for_quant_eval` 可开启上游可视化，
此时需要准备 `.blend` 场景。其它参数直接传给上游 Python 入口。

构建验证包括：`pip check`、PyTorch3D 原生扩展的 CPU KNN 运算、BPS 编码、
三个模型的入口导入/CLI 检查、Blender 后台启动，以及无权重检查。
GitHub hosted runner 没有 GPU，因此这些检查不代表已完成带权重的 GPU 推理验证。
