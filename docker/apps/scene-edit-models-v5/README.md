# Scene Edit Models V5

基于 V4，保留 SkinTokens、Kimodo、Qwen3-VL、Blender、GVHMR、Motion2MixamoRig 和 TRELLIS.2，并新增：

| 模型 | Conda 环境 | 源码路径 |
| --- | --- | --- |
| InterPose | `interpose` | `/app/InterPose` |
| InterPose 的 MaskedMimic / ProtoMotion | `protomotions_interpose` | `/app/InterPose/third-party/ProtoMotion_for_InterPose` |
| LIGHT | `light` | `/app/LIGHT` |

镜像不包含模型权重、SMPL/SMPL-X 或数据集。MaskedMimic 需要 Isaac Gym Preview 4、NVIDIA GPU、上游 checkpoint 及 SMPL 模型；LIGHT 需要上游 checkpoint、数据和 SMPL+H/SMPL-X。具体路径和运行方式见上游 README。使用 `conda activate <环境名>` 切换环境。
