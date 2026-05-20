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
- Prefer the existing `docker/vggt-omega/Dockerfile` and other nearby model Dockerfiles as style references
- Prefer `.github/workflows/docker-vggt-omega.yml` as the workflow reference (latest dual-build pattern)
- In the same workflow, build the runtime image with `docker/build-push-action@v6` using `push: ${{ github.event_name != 'pull_request' }}` — the runtime is streamed straight to GHCR with no local `load`. Include `ghcr.io/wangxinjian1108/<repo-name>:sha-<short>` in the tag list so the dev step has a stable remote tag to pull from.
- Build the dev image with a second `docker/build-push-action@v6` step, gated on `if: github.event_name != 'pull_request'`. Pass `build-args: BASE_IMAGE=ghcr.io/wangxinjian1108/<repo-name>:sha-<short>` so buildx pulls the just-pushed runtime layers on demand. Use a separate cache scope (e.g. `cache-to: type=gha,mode=max,scope=dev`) so runtime and dev caches don't clobber each other.
- Do **not** use `load: true` on the runtime build. `load` writes the full image as a tarball to local docker, which OOM-disks GitHub-hosted runners (~14 GB free) on any model image bigger than ~10 GB (CUDA-devel base + torch + weights are usually enough on their own).
- On pull requests, the dev step is skipped (no pushed runtime to pull from); CI only verifies the runtime build. Document this trade-off; if PR-time dev validation is required, build runtime with `outputs: type=cacheonly` and dev with the same cache, but expect longer CI.
- Do not create a separate `<repo-name>-dev` image repository — use the same GHCR repo with the `:dev` tag

## Done criteria

- Submodule exists at `thirdparty/<repo-name>`
- Dockerfile and workflow exist and are coherent
- Runtime and dev Dockerfiles exist
- One workflow builds both runtime and dev images in order
- `IMAGES.md` includes the new image
- Changes are committed and pushed
- CI status is reported, with remaining blockers called out explicitly if any
