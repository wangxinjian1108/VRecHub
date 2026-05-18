# train-test Skill 说明

## 用途

在已构建的 Docker 镜像中验证端到端训练流程：拉取镜像、准备 dev 分支、转换原始数据、运行 1 个完整 epoch，确认 pipeline 可用。

## 调用方式

```
/train-test <model-name> [data-path]
```

示例：
- `/train-test vggt /root/data/recons_dataset`
- `/train-test Pi3`（不提供 data-path 会交互式询问）

## 完整流程

### 1. 解析与验证
- 解析模型名和数据路径
- 验证 `thirdparty/<model>` 在 `.gitmodules` 中存在
- 验证数据路径存在且包含 `raw/` 子目录

### 2. 准备镜像
- 拉取 `ghcr.io/wangxinjian1108/<model>:latest`
- 拉取失败时提示先构建镜像（触发 workflow 或运行 `/dockerize-submodule`）

### 3. 准备 Repo（dev 分支）
- 进入 `thirdparty/<model>` 子模块
- 如果 dev 分支存在：checkout 并 pull
- 如果不存在：从当前 HEAD 创建 `dev` 分支
- 确保 `data_prepare/` 目录存在

### 4. 准备数据
1. **发现数据集** — 列出 `<data-path>/raw/` 下的非空目录，让用户多选要处理哪些
2. **理解模型数据格式** — 阅读模型训练代码，了解期望的数据格式
3. **编写转换脚本** — 为每个选中的数据集创建 `data_prepare/prepare_<dataset>.py`
   - 接受 `--raw` 和 `--output` 参数
   - 自包含，只用镜像内已有的依赖
4. **在容器内运行转换** — 挂载数据和代码目录，执行转换脚本
   - 输出到 `<data-path>/processed/<model>/<dataset>`
   - 失败最多重试 3 次

### 5. 闭环训练测试
1. **创建测试训练配置** — 基于模型已有配置，修改为：
   - 数据路径指向 `/data/processed/<model>/`
   - `max_epochs: 1`
   - 小 batch size（单卡）
   - 关闭 wandb 等非必要功能
2. **在容器内运行训练** — 使用测试配置跑 1 个 epoch
3. **评估结果** — 1 个完整 epoch 无报错即为成功；失败最多重试 3 次

### 6. 提交 Dev 分支
- 训练成功后，在子模块的 dev 分支上 commit 并 push 所有新增/修改的文件

### 7. 报告
- 处理了哪些数据集及大小
- 训练结果（成功/失败及原因）
- dev 分支上提交了什么
- 需要人工关注的问题

## 核心思路

这个 skill 的设计目标是：**在不污染主分支的前提下，用 Docker 容器隔离环境，自动化地验证一个模型子模块的训练流程是否能跑通**。所有实验性代码都在子模块的 `dev` 分支上，数据转换和训练都在容器内执行。
