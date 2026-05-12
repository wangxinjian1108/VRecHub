罗列所有已推送到 GitHub Container Registry 的 Docker 镜像及其对应论文，以表格形式输出到 `IMAGES.md`。

## Steps

1. **收集镜像信息** — 扫描 `.github/workflows/docker-*.yml` 文件，提取每个镜像的名称。镜像地址格式为 `ghcr.io/wangxinjian1108/<name>`。

2. **收集版本信息** — 对每个镜像对应的 `docker/<name>/Dockerfile`，提取：
   - CUDA 版本（FROM 行中的 `cuda:XX.X`）
   - PyTorch 版本（`torch==X.X.X`，未锁定则标注 `latest`）

3. **收集论文信息** — 对每个镜像对应的 submodule（`thirdparty/<name>`），读取其 README 文件，提取论文标题和 arXiv/PDF 链接。

4. **生成表格** — 写入 `IMAGES.md`，包含以下 6 列，按项目名称字母排序：

   | 项目 | Docker 镜像 | CUDA | PyTorch | 论文 | 描述 |
   |------|------------|------|---------|------|------|

   - 如果某个项目没有对应论文，在论文列标注"无独立论文"并注明参考项目
   - 文件末尾附一行统计：共 N 个镜像

5. **输出确认** — 打印 "IMAGES.md updated" 和镜像总数。
