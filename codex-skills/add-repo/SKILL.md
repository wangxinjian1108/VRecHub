---
name: add-repo
description: Add a new git submodule to the VRecHub-style reconstruction hub, generate its Dockerfile and GitHub Actions image workflow, update the image index, commit, push, and watch CI. Use when the user gives a repo SSH URL or asks for the full add-repo pipeline.
---

# Add Repo

Use this skill when the user wants the full onboarding flow for a new model repository.

## Inputs

- A git SSH URL such as `git@github.com:org/repo-name.git`

## Repo assumptions

- Main repo branch is `master`
- Submodules live under `thirdparty/<name>`
- Dockerfiles live under `docker/<name>/Dockerfile`
- Image workflows live under `.github/workflows/docker-<name>.yml`
- Image names use lowercase repo names under `ghcr.io/wangxinjian1108/<name>`

## Guardrails

- Read `AGENTS.md` first if it exists
- Never stage secrets such as `.env`, `config/token.yaml`, or large binaries
- Do not revert unrelated user changes in the worktree

## Workflow

1. Resolve `<repo-name>` from the SSH URL by taking the last path segment without `.git`.
2. Check `.gitmodules` and `thirdparty/<repo-name>`.
3. If the submodule already exists, update it with `git submodule update --init --remote thirdparty/<repo-name>`.
4. If it does not exist, add it with `git submodule add <ssh-url> thirdparty/<repo-name>` and then initialize recursively.
5. Generate `docker/<repo-name>/Dockerfile` and `docker/<repo-name>/Dockerfile.dev`.
6. Generate one workflow at `.github/workflows/docker-<repo-name>.yml`.
7. Follow the `dockerize-submodule` workflow for runtime dependency detection, CUDA selection, workflow triggers, and registry publishing.
8. Follow the `dev-image` workflow for the dev Dockerfile and for adding the dev-image build to the same workflow.
9. Refresh `IMAGES.md` by following the `list-images` workflow.
10. Stage the submodule pointer, `.gitmodules`, Dockerfiles, workflow, and `IMAGES.md`.
11. Commit with `feat: add <repo-name> Dockerfile and workflow` unless the user asked for different wording.
12. Push to the current default remote branch.
13. Watch the triggered CI run. If it fails, inspect failed logs, fix code or workflow issues, and retry up to 3 rounds.

## Dockerization requirements

- Build context must be the repo root
- Copy source from local submodules, never `git clone` during image build
- Prefer the existing `docker/vggt/Dockerfile` and other nearby model Dockerfiles as style references
- Prefer the existing `.github/workflows/docker-*.yml` files as workflow references
- In the same workflow, build the runtime image first, tag it with a local runtime tag, build `ghcr.io/wangxinjian1108/<repo-name>:dev` from that local runtime tag, then push the runtime and dev tags
- After pushing the runtime tags and before building the dev image, free runner disk: `docker image prune -af --filter "label!=local-runtime"` (or equivalent — remove every local image except the `<repo-name>:runtime-<shortsha>` tag and any layers buildx still needs). The dual-build pattern keeps the full runtime image in the local daemon for `--build-arg BASE_IMAGE=`, so on GitHub-hosted runners (~14 GB free) the dev export step will OOM-disk without this prune.
- Do not create a separate `<repo-name>-dev` image repository

## Done criteria

- Submodule exists at `thirdparty/<repo-name>`
- Dockerfile and workflow exist and are coherent
- Runtime and dev Dockerfiles exist
- One workflow builds both runtime and dev images in order
- `IMAGES.md` includes the new image
- Changes are committed and pushed
- CI status is reported, with remaining blockers called out explicitly if any
