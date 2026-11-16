# CHOIS + OMOMO + Kimodo 离线权重镜像

完整的拉取、挂载、自检和三个模型的推理说明见
[human-object-interaction-v1 使用与推理指南](../../../docs/usage/human-object-interaction-v1.md)。

无权重环境镜像通过 GitHub Actions 构建，固定 base digest：
`sha256:bd956d166bcf92367096c281fe5bf6902e82566e579094d189420dbebc8637b2`。
最终带权重镜像在目标机器上通过 `Dockerfile.local` 构建，避免把约 15 GiB
权重层上传到 GitHub Packages。运行时也不需要 HTTP 文本编码服务。

- GHCR：`ghcr.io/wangxinjian1108/human-object-interaction-v1:with-weights`
- 固定构建标签：`weights-sha-<commit>`
- 内网分发：`repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest`
- 无权重版的 GHCR `:latest` 保留。

`docker-human-object-interaction-v1-weights.yml` 只保留为手动恢复路径；
自动 CI 只维护 `docker-human-object-interaction-v1.yml` 中的基础环境。

## 本机构建最终镜像

先确认 `docker/apps/human-object-interaction-v1-weights/download-weights.py`
生成的 `/models/weights-manifest.json` 存在，然后执行：

```bash
./docker/apps/human-object-interaction-v1-weights/build-local.sh \
  /root/models/human-object-interaction-v1 \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest
```

脚本把已从 GHCR 拉取的基础镜像标为 `local/human-object-interaction-v1:base`，
再通过 BuildKit named context 只加入本机权重，不会从 GitHub 重新下载模型。

网络无法稳定续传单一大层时，先拉取已拆成约 900 MiB OCI 层的权重传输镜像，
再合并并逐文件校验：

```bash
./docker/apps/human-object-interaction-v1-weights/materialize-weights.sh \
  /root/models/human-object-interaction-v1
```

需要为本机、Zelos 内网或推理使用方单独同步较大权重时，可拉取
`ghcr.io/wangxinjian1108/human-object-interaction-v1-weights-chunks:latest`；
该镜像不是推理环境，只保存可逐层续传的权重分块。

| 模型 / 依赖 | 镜像内路径 |
|---|---|
| CHOIS 官方 model-10.pt | `/models/chois/model-10.pt` |
| OMOMO 标准两阶段 | `/models/omomo/stage1/model.pt`、`/models/omomo/stage2/model.pt` |
| OMOMO object-split 两阶段 | `/models/omomo/stage1_object_split/model.pt`、`/models/omomo/stage2_object_split/model.pt` |
| CLIP ViT-B/32 | `/models/clip/ViT-B-32.pt` |
| Kimodo SOMA-RP v1.2（上游默认模型） | `/models/kimodo/Kimodo-SOMA-RP-v1.2/` |
| Llama 3 8B Instruct 基础模型 | `/models/text-encoders/meta-llama/Meta-Llama-3-8B-Instruct/` |
| LLM2Vec MNTP 和 supervised 适配器 | `/models/text-encoders/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp{,-supervised}/` |

`weights.lock.json` 固定所有 Hugging Face revision、文件大小及哈希。
CHOIS 和 OMOMO 使用论文作者提供的 Google Drive 资源，并检查固定 SHA256。
Llama 基础权重取自公开的 `NousResearch/Meta-Llama-3-8B-Instruct`；四个
safetensors 分片的 SHA256 均与 Meta 官方 `8afb486c1db24fe5011ec46dfbe5b5dccdb575c2`
版本一致。模型许可证和使用条款随权重保存。

安装后的逐文件 SHA256 清单：`/models/weights-manifest.json`。
适配器配置中的基础模型路径已改为 `/models` 内路径；保留原始 `_name_or_path`
以维持 LLM2Vec 的指令格式。默认 `TEXT_ENCODER_MODE=local`、
`HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`。

## 运行

Kimodo 可直接使用打包的模型和本地文本编码器：

```bash
docker run --rm --gpus all \
  -v "$PWD/outputs:/outputs" \
  repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v1:latest \
  kimodo-gen 'A person walks forward.' \
  --duration 2 --num_samples 1 --output /outputs/walk --seed 42
```

8B 文本编码器需要额外显存。显存不足时可用 `-e TEXT_ENCODER_DEVICE=cpu`，
此时需要足够的主机内存。不要把空宿主目录挂到整个 `/models`，否则会遮住内置权重。

CHOIS/OMOMO 还需要输入数据、SMPL-H/SMPL-X 人体资源和可选的渲染场景；
这些不属于本次模型权重包，需要按原环境镜像 README 的布局挂载。
`SMPLH_PATH=/models/smplh_amass`；人体模型需要放到各数据根目录的
`smpl_all_models/`。CHOIS 单窗口示例：

```bash
chois-infer --batch_size=1 \
  --data_root_folder=/data/chois --save_res_folder=/outputs/chois
```

入口已添加官方 checkpoint 对应的语言、对象关键点及引导参数。
OMOMO 默认标准两阶段；object-split 使用：

```bash
omomo-infer --batch_size=1 --data_root_folder=/data/omomo \
  --project=/outputs/omomo --exp_name=stage1 --fullbody_exp_name=stage2 \
  --checkpoint=/models/omomo/stage1_object_split/model.pt \
  --fullbody_checkpoint=/models/omomo/stage2_object_split/model.pt \
  --use_object_split --for_quant_eval
```

CPU 构建验证会载入 CHOIS/OMOMO 的训练和 EMA 权重，检查所有推理参数均匹配；
CHOIS checkpoint 中上游推理不用的 body-shape/contact 辅助头允许存在。
还检查 CLIP 实际文本编码、Kimodo 动作模型加载、Llama 分片索引、两个适配器、
CLI、pip check 和 Blender。构建检查不等同于完整 GPU 端到端验证。

## 单独下载到宿主机

```bash
python3 -m pip install gdown==5.2.0 requests
python3 docker/apps/human-object-interaction-v1-weights/download-weights.py \
  --root /root/models/human-object-interaction-v1
```

也可从已拉取的镜像用 `docker create`、`docker cp <container>:/models/. <目录>`
取出相同权重，随后删除临时容器。
