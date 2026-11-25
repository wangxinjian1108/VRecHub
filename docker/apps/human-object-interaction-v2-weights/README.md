# Human Object Interaction V2：本地权重层

环境来自 GitHub Actions 已发布的 V2，权重在本机添加，内网目标为
`repo-volc.zelostech.com.cn/zcloud/human-object-interaction-v2:latest`。

- `Dockerfile.local`：复用已发布 V1 中的 CHOIS、OMOMO、Kimodo、CLIP 和 Llama/LLM2Vec 权重，保留 V2 环境。
- `weights.lock.json`：新增公开权重的固定版本、大小和上游校验值。
- `download.py --group <group> --root <host-staging>`：断点下载一个分组，校验 HF LFS SHA256 或 Git blob SHA1。大文件按范围下载；代理仅用于下载，不会成为镜像运行时依赖。
- `download.py --configure`：在容器内展开 checkpoint 压缩包、建立上游目录和 HF 离线缓存链接。
- `verify.py --write-manifest`：验证继承权重、下载文件、解压文件 CRC 和目录链接，写入 `/models/weights-manifest-v2.json`。

宿主下载器需要 `requests`，使用 SOCKS 代理时另需 `PySocks`。默认直连；需要代理
时通过 `HOI_HTTP_PROXY`（Google Drive）和 `HOI_SOCKS_PROXY`（二进制下载）设置，
不要把代理凭据写入 lock 文件或镜像。

镜像很大。空间不足时，逐组将下载结果 `docker cp` 到专用容器、`docker commit`，
每次提交后移除该专用容器并从新提交启动下一个容器。只删除已提交的同组临时下载，
不要清理其他镜像或用户数据。HF 缓存和各项目目录使用符号链接，避免重复存放权重。

公开文件不包含受许可限制的 SMPL-H、SMPL-X、DMPL。HAIC 的公开权重为
`Cybercal/HOIC-baseline` 的 7 个 MuJoCo ONNX 策略，不能用来替代
`/app/HAIC/scripts/play.py` 需要的 Isaac Sim PyTorch checkpoint。

使用方法及验证结果见 `docs/usage/human-object-interaction-v2.md`。
