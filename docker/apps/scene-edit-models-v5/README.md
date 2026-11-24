# Scene Edit Models V5

基于 V4，保留 SkinTokens、Kimodo、Qwen3-VL、Blender、GVHMR、Motion2MixamoRig 和 TRELLIS.2，新增 LIGHT。

LIGHT 位于 `/app/LIGHT`，使用独立的 `light` Conda 环境（Python 3.10，PyTorch 2.5.1）。镜像不包含 LIGHT checkpoint、数据集和 SMPL+H/SMPL-X 人体模型；这些文件需要按 LIGHT 上游 README 准备并挂载。

```bash
conda activate light
cd /app/LIGHT
bash scripts/generate.sh --dataset omomo
```

推理还需要 GPU、预训练模型、指定的数据集和人体参数。完整说明见 [LIGHT 上游文档](https://github.com/wzyabcas/LIGHT)。
