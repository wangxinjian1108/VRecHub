---
name: list-images
description: Rebuild IMAGES.md for a VRecHub-style repository by scanning Docker workflows, Dockerfiles, and submodule READMEs to produce an image and paper index table. Use when the image catalog needs to be refreshed.
---

# List Images

Use this skill when the user asks to regenerate `IMAGES.md`.

## Workflow

1. Scan `.github/workflows/docker-*.yml` to identify all published runtime image names.
2. Ignore dev-image workflows such as `docker-<name>-dev.yml` unless the user explicitly asks for a dev image catalog.
3. For each image, inspect `docker/<name>/Dockerfile` and extract:
   - CUDA version from `FROM`
   - PyTorch version if pinned, otherwise mark `latest` or `unspecified`
4. Inspect the corresponding submodule README under `thirdparty/<name>` and extract:
   - paper title
   - arXiv or PDF link
   - a short description
5. Generate `IMAGES.md` as a table with columns:
   - 项目
   - Docker 镜像
   - CUDA
   - PyTorch
   - 论文
   - 描述
6. Sort rows by project name unless the repo already uses another stable order.
7. If a project has no standalone paper, state that plainly in the paper column.
8. Add a final count line such as `共 N 个镜像`.

## Guardrails

- Prefer repo files over memory
- Keep existing formatting style if `IMAGES.md` already exists
- Do not invent paper metadata when the README is ambiguous; mark it as unknown instead

## Done criteria

- `IMAGES.md` is updated
- The total image count matches the number of discovered workflows or the gap is explained
