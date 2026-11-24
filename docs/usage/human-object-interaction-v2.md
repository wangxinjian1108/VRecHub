# Human Object Interaction V2 候选镜像

该候选镜像通过 GitHub Actions 构建和组合，包含 LIGHT、InterAct、GRAIL、
HAIC、CHOIS、OMOMO、Kimodo 和 Blender。候选镜像的清单与各来源层已核对；
完整容器验证结果应以 Actions 的检查任务为准，不应把候选版本视为已验证的
正式发布。

目前已在 GitHub Actions 中用相同的四个环境层验证 CHOIS、OMOMO、
Kimodo、LIGHT、InterAct 和 HAIC 在同一测试容器内的导入与入口；GRAIL
独立运行时的构建和 CPU 组件检查也已通过。前一项测试使用较小的验证
基础镜像，不包含 GRAIL，不能替代完整聚合镜像的运行验证。对应记录为
[组合环境检查](https://github.com/wangxinjian1108/VRecHub/actions/runs/45428747111)
和 [GRAIL 构建](https://github.com/wangxinjian1108/VRecHub/actions/runs/45395578227)。
完整镜像的 GitHub 托管节点检查在拉取阶段耗尽磁盘空间，尚未执行容器测试；
详见 [检查记录](https://github.com/wangxinjian1108/VRecHub/actions/runs/45419274165)。

```text
ghcr.io/wangxinjian1108/human-object-interaction-v2@sha256:72781fbc45e4087df7c020308d0fcea4c61dc3aff705ec25ae1738337ecbfdb7
```

压缩镜像层约 59.8 GiB，解压和运行还需要额外空间。GRAIL 上游测试环境为
48 GB 显存的 RTX 6000 Ada 和 595.99.02 驱动；上游记录的部分场景重建
超过 24 GiB。本机 L4 的驱动为 550.144.03，不能据此认定 GRAIL 或 HAIC
仿真在本机可运行。

此镜像没有主动打入上述模型的预训练权重、完整数据集或受许可限制的
SMPL-H／SMPL-X 人体模型。各模型还需要按上游说明准备对应 checkpoint、
数据和人体模型；GRAIL 的示例数据含 Git LFS 文件，也需另行准备。

## 启动与环境

```bash
docker pull ghcr.io/wangxinjian1108/human-object-interaction-v2@sha256:72781fbc45e4087df7c020308d0fcea4c61dc3aff705ec25ae1738337ecbfdb7

docker run --rm -it --gpus all --shm-size=16g \
  -v /data/hoi-models:/models \
  -v /data/hoi-output:/outputs \
  ghcr.io/wangxinjian1108/human-object-interaction-v2@sha256:72781fbc45e4087df7c020308d0fcea4c61dc3aff705ec25ae1738337ecbfdb7 \
  bash
```

将上例宿主机路径替换为实际路径。进入容器后，CHOIS 和 OMOMO 使用
`hoi` 环境，LIGHT、InterAct、HAIC 分别使用 `light`、`interact`、`haic`
环境；这些环境位于 `/opt/conda/envs/`。GRAIL 的 `grail`、`hunyuan`、
`sonic` 环境位于 `/root/miniconda3/envs/`，例如：

```bash
conda run -n light python -c 'import torch; print(torch.__version__)'
/root/miniconda3/bin/conda run -n grail python -c 'import torch; print(torch.__version__)'
```

GRAIL 的 GEM-X 环境位于 `/root/.cache/grail/envs/gem-x`，不要将宿主机目录
直接挂载到整个 `/root/.cache`，否则会遮住它。默认 `blender` 是 CHOIS 使用
的 Blender 3.6.3；GRAIL 使用的 Blender 4.3.2 位于
`/workspace/grail/imports/blender/blender`。

## 各模型入口

- **LIGHT**：将人体模型挂载到 `/app/LIGHT/models`，模型 checkpoint 和数据
  按 [LIGHT 上游说明](https://github.com/wzyabcas/LIGHT) 放置。从
  `/app/LIGHT` 在 `light` 环境内运行 `bash scripts/generate.sh --dataset omomo`，
  或按上游说明选择其他数据集与 guidance。
- **InterAct**：将人体模型挂载到 `/app/InterAct/models`，checkpoint 和数据
  按 [InterAct 上游说明](https://github.com/wzyabcas/InterAct) 放置。从
  `/app/InterAct/text2interaction` 使用 `interact` 环境运行
  `bash scripts/run_sample_nonguide.sh` 或相应的 guidance 脚本。
- **GRAIL**：从 `/workspace/grail` 使用 `/root/miniconda3` 中的 `grail`
  环境。权重、示例数据与完整工作流见
  [GRAIL 下载说明](https://github.com/NVlabs/GRAIL/blob/main/docs/source/downloads.md)。
- **HAIC**：从 `/app/HAIC` 使用 `haic` 环境运行上游 `scripts/play.py`；
  需提供与任务相匹配的策略 checkpoint、仿真数据和兼容 Isaac Sim 的 GPU／驱动。
  参见 [HAIC 上游说明](https://github.com/ldt29/HAIC)。
- **CHOIS 和 OMOMO**：入口分别为 `chois-infer`、`omomo-infer`。此候选镜像
  继承的是无权重环境版本，调用时须按上游配置明确提供 checkpoint 和数据路径。
  两者的权重采样复测及其局限见
  [验证记录](human-object-interaction-validation.md)。

LIGHT 与 InterAct 上游代码在解析参数前会加载 SMPL-H，因此在没有按上游
目录挂载真实人体模型时，连推理脚本的 `--help` 都可能报错。构建时的入口
检查只在测试进程中临时模拟人体模型创建，实际推理不会使用模拟对象。

## GPU 基础检查

在本仓库根目录，可以将检查脚本挂入已拉取的候选镜像，例如测试 LIGHT：

```bash
docker run --rm --gpus all --network none \
  -v "$PWD/scripts/hoi/check_gpu.py:/tmp/check_gpu.py:ro" \
  --entrypoint /opt/conda/envs/light/bin/python \
  ghcr.io/wangxinjian1108/human-object-interaction-v2@sha256:72781fbc45e4087df7c020308d0fcea4c61dc3aff705ec25ae1738337ecbfdb7 \
  /tmp/check_gpu.py light
```

脚本接受 `hoi`、`light`、`interact`、`haic`、`grail`。前四项对应
`/opt/conda/envs/<环境名>/bin/python`；GRAIL 使用
`/root/miniconda3/envs/grail/bin/python`。该检查执行简单的 CUDA 运算，
并对适用环境测试 PyTorch3D、PointNet2 或 nvdiffrast；它不加载模型权重，
也不替代真实数据上的完整生成或仿真测试。
