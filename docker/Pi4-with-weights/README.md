# Pi4 带权重镜像

通过 GitHub Actions 基于已发布的 Pi4 环境镜像加入官方权重 `yyfz233/Pi4`，
不在本地构建正式镜像。权重 revision `59f307317fb630c9c5a5aa635038d98ed106aaf5`，
SHA-256 `fefacac1fb3d23d33c628c41f40d3ce3be98ca064c271948371805db7b5a0e69`。
权重位于 `/models/Pi4/model.safetensors`，同时填充 Hugging Face 本地缓存，默认
推理可离线加载。使用说明见 [Pi4 推理指南](../../docs/usage/pi4.md)。
