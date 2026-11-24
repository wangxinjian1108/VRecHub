# CHOIS 和 OMOMO 权重采样验证

2026-11-24，在 NVIDIA L4（驱动 550.144.03）上，使用本机镜像
`repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest`
（镜像摘要 `sha256:3799d4fe1c22029ed1fc2447476c3ef9ed4605c5f3088b730611d534fea3fbcd`）
执行了离线 GPU 测试。测试输入为合成的 120 帧序列，运行模型自带的
完整 1,000 步采样循环，检查输出形状和有限值。

| 模型与权重 | 输出形状 | 结果 |
| --- | --- | --- |
| CHOIS，`model-10.pt` | `(1, 120, 220)` | 通过 |
| OMOMO 第一阶段，标准权重 | `(1, 120, 6)` | 通过 |
| OMOMO 第二阶段，标准权重 | `(1, 120, 204)` | 通过 |
| OMOMO 第一阶段，object-split 权重 | `(1, 120, 6)` | 通过 |
| OMOMO 第二阶段，object-split 权重 | `(1, 120, 204)` | 通过 |

CHOIS 测试同时加载镜像内的 CLIP 权重，对文本 `a person carries a box`
编码后输入模型。所有测试均禁用容器网络，使用镜像内的 EMA 权重。

这些测试验证权重加载、CUDA 执行和模型采样路径；合成输入并不验证动作
语义、两阶段衔接、数据预处理、人体网格或渲染。完整的真实数据推理还需要
上游预处理数据和经许可获取的 SMPL-H / SMPL-X 模型，见
[V1 使用说明](human-object-interaction-v1.md)。

2026-11-25 还在上述 V1 镜像中验证了 `hoi` 环境的 PyTorch3D CUDA 最近邻
算子：NVIDIA L4 上通过，PyTorch 为 1.11.0，使用 CUDA 11.3 构建。V2
完整镜像的同项检查需要等其拉取完成后单独运行。

在仓库根目录可用以下命令复现 CHOIS 测试：

```bash
docker run --rm --gpus all --network none --shm-size=4g \
  -v "$PWD/scripts/hoi/test_weighted_denoisers.py:/tmp/test.py:ro" \
  -w /app/chois_release --entrypoint /opt/conda/envs/hoi/bin/python \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  /tmp/test.py chois /models/chois/model-10.pt --sample-steps 1000 --frames 120
```

OMOMO 测试使用相同镜像和脚本，工作目录改为 `/app/omomo_release`，
参数分别为：

```text
stage1 /models/omomo/stage1/model.pt
stage2 /models/omomo/stage2/model.pt
stage1 /models/omomo/stage1_object_split/model.pt
stage2 /models/omomo/stage2_object_split/model.pt
```

各项均加 `--sample-steps 1000 --frames 120`。

## OMOMO 两阶段衔接

2026-11-25，在同一台 L4 和上述带权重镜像中，使用合成输入分别测试了标准
权重和 object-split 权重的两阶段连续采样。第一阶段生成 `(1, 120, 6)`
的双手位置后，按上游 `gen_fullbody_from_predicted_hand_foot` 的位置和
掩码放入第二阶段条件；第二阶段生成 `(1, 120, 204)` 的全身运动。两个
阶段均运行完整的 1,000 步采样，输出形状和有限值检查通过。

该检查验证阶段之间的张量衔接和采样调用，并不验证真实物体数据、动作质量、
人体网格或渲染。可从仓库根目录复现标准权重测试：

```bash
docker run --rm --gpus all --network none --shm-size=4g \
  -v "$PWD/scripts/hoi/test_omomo_two_stage.py:/tmp/test_two_stage.py:ro" \
  -w /app/omomo_release --entrypoint /opt/conda/envs/hoi/bin/python \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  /tmp/test_two_stage.py /models/omomo/stage1/model.pt \
  /models/omomo/stage2/model.pt --frames 120
```

测试 object-split 权重时，分别将两个权重路径替换为
`/models/omomo/stage1_object_split/model.pt` 和
`/models/omomo/stage2_object_split/model.pt`。

## Blender 无头渲染

2026-11-25，使用上述带权重的 V1 镜像，在无网络容器中运行 Blender 3.6.3
的 CPU Cycles 渲染，并检查生成的 64 × 64 PNG 的尺寸和图像内容，结果通过。
这项检查也已加入 V2 候选镜像的本机验证脚本；V2 的完整容器结果以该脚本
实际运行结果为准。

```bash
docker run --rm --network none \
  -v "$PWD/scripts/hoi/check_blender.py:/tmp/check_blender.py:ro" \
  --entrypoint /opt/blender/blender \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  --background -noaudio --python-exit-code 1 --python /tmp/check_blender.py
```
