---
name: train-test
description: Validate end-to-end training for a model in a VRecHub-style repository by using the published container, preparing dataset conversion scripts on the submodule dev branch, running one small training epoch in Docker, and reporting the result. Use when the user asks to verify a model training pipeline without polluting the main branch.
---

# Train Test

Use this skill when the user asks to verify that a model can train end to end inside its published image.

## Inputs

- `<model>`
- optional `<data-path>`

## Core constraint

- Experimental code belongs on the submodule’s `dev` branch
- Data conversion and training run inside Docker
- Do not mutate the main repo `master` branch just to carry temporary training scripts
- Only update the main repo when the user explicitly wants Dockerfile, workflow, or submodule-pointer changes shipped

## Validation

1. Confirm `thirdparty/<model>` exists.
2. Confirm the data path exists and contains `raw/`.
3. Pull `ghcr.io/wangxinjian1108/<model>:latest`.
4. If the image does not exist:
   - if `.github/workflows/docker-<model>.yml` exists, tell the user to build or trigger it
   - otherwise suggest running the dockerization workflow first

## Dev branch setup

1. Enter `thirdparty/<model>`.
2. Checkout `dev` if it exists locally or remotely.
3. Otherwise create `dev` from the current HEAD.
4. Ensure `data_prepare/` exists.

## Dataset preparation workflow

1. Discover non-empty dataset folders under `<data-path>/raw/`.
2. If multiple datasets exist and the user did not specify which ones, ask.
3. Read the model’s training code and configs to determine the expected dataset structure.
4. For each selected dataset, create `data_prepare/prepare_<dataset>.py`.
5. Each prep script must:
   - accept `--raw` and `--output`
   - use only dependencies expected inside the container
   - print enough progress to debug failures
6. Run each prep script in Docker, writing outputs to `<data-path>/processed/<model>/<dataset>`.
7. Retry and fix prep issues up to 3 times per dataset.

## Training workflow

1. Derive a minimal train config from the model’s existing config system.
2. Change only what is needed:
   - data path to `/data/processed/<model>/...`
   - `max_epochs=1` or equivalent
   - small single-GPU batch size
   - disable wandb or similar external logging if possible
3. Run one training epoch in Docker with mounted code and data.
4. Success means the epoch completes without crashing.

## Missing dependency loop

If training fails because the image is missing dependencies:

1. Confirm the error is truly image-level, not data-level or code-level.
2. Debug quickly in a local container.
3. Translate the discovered fix back into `docker/<model>/Dockerfile`.
4. If needed, adjust `.github/workflows/docker-<model>.yml`.
5. Rebuild or trigger CI for a fresh `latest` image.
6. Pull the rebuilt image and rerun training to verify the formal fix.

## Commit policy

- Commit dataset prep scripts and test configs to the submodule `dev` branch after success
- Push `dev`
- Do not merge `dev` to `master` automatically
- Only update the parent repo’s submodule pointer if the user explicitly asks to ship that result

## Report

Always report:

- datasets processed
- where processed outputs were written
- whether 1 epoch succeeded
- which files were added on `dev`
- whether Dockerfile or workflow changes were required
- what still needs manual attention
