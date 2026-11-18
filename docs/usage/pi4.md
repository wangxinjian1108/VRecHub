# Pi4 镜像推理

Pi4 从图像或视频重建场景几何，支持相机位姿估计和跨帧稠密跟踪。镜像由 GitHub Actions 构建：`ghcr.io/wangxinjian1108/pi4:latest`。

- Linux x86-64，NVIDIA GPU 和 NVIDIA Container Toolkit；GPU 需要支持 BF16，NVIDIA 驱动需兼容 CUDA 12.6。
- 镜像使用 Python 3.11、PyTorch 2.12.1 + CUDA 12.6、Triton 3.7.1 和上游固定版本的 FlexGEMM。
- **镜像不包含权重。**默认从 Hugging Face `yyfz233/Pi4` 下载并缓存，或使用已下载的 `model.safetensors`。上游代码和权重均为 CC BY-NC 4.0，使用前请查看上游许可。

拉取并检查：

```bash
docker pull ghcr.io/wangxinjian1108/pi4:latest
docker run --rm --gpus all ghcr.io/wangxinjian1108/pi4:latest \
  python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0), 'BF16:', torch.cuda.is_bf16_supported())"
```

自动下载权重并处理本地视频；挂载缓存可以避免重复下载：

```bash
mkdir -p "$PWD/pi4-work" "$PWD/pi4-hf-cache"
docker run --rm --gpus all \
  -v "$PWD/pi4-work:/work" \
  -v "$PWD/pi4-hf-cache:/root/.cache/huggingface" \
  ghcr.io/wangxinjian1108/pi4:latest \
  python example.py /work/input.mp4 --output /work/result \
  --query-frame 0 --stride 1 --max-frames 25 --viewer
```

请先将视频放到 `pi4-work/input.mp4`。结果目录必须不存在；删掉 `--query-frame 0` 可仅输出几何重建。显存使用取决于分辨率和帧数，建议从少量帧开始。

如果 Hugging Face 不可访问，可把权重放在 `pi4-work/model.safetensors`，并在命令末尾追加 `--weights /work/model.safetensors`。结果可使用镜像中的浏览器查看器打开：

```bash
docker run --rm -p 8080:8080 -v "$PWD/pi4-work:/work" \
  ghcr.io/wangxinjian1108/pi4:latest \
  python viewer/serve.py /work/result --host 0.0.0.0 --port 8080
```

完整输入、输出和性能说明见 submodule 的 `thirdparty/Pi4/docs/inference.md`。
