Validate end-to-end training inside a built Docker image: pull image, prepare dev branch, convert raw data, and run 1 full epoch to confirm the pipeline works.

## Argument
`$ARGUMENTS` is `<model-name> [data-path]`. Model name is required; data path is optional (will ask interactively if omitted).

Examples:
- `/train-test vggt /root/data/recons_dataset`
- `/train-test Pi3`

## Steps

### 1. Parse & Validate

- Split `$ARGUMENTS` into model name (first token) and optional data path (second token).
- Verify `thirdparty/<model>` exists in `.gitmodules`. If not, list available submodules and stop.
- If data path was not provided, use AskUserQuestion to ask the user for it.
- Verify the data path exists and contains a `raw/` subdirectory. If not, stop with an error.

### 2. Prepare Image

- Image name: `ghcr.io/wangxinjian1108/<model>:latest`
- Pull: `docker pull ghcr.io/wangxinjian1108/<model>:latest`
- If pull fails, check if `.github/workflows/docker-<model>.yml` exists:
  - If yes: suggest the user trigger the workflow first (`gh workflow run docker-<model>.yml`)
  - If no: suggest running `/dockerize-submodule <model>` first
  - Stop in either case.

### 3. Prepare Repo (dev branch)

- Enter the submodule: `cd thirdparty/<model>`
- Check for existing dev branch:
  - Remote: `git branch -r | grep origin/dev`
  - Local: `git branch | grep dev`
- If dev exists (remote or local): `git checkout dev && git pull origin dev`
- If dev does not exist: `git checkout -b dev` (branches from current HEAD)
- Create `data_prepare/` directory if it doesn't exist: `mkdir -p data_prepare`
- Return to repo root.

### 4. Prepare Data

**4a. Discover available datasets**
- List directories under `<data-path>/raw/` that are non-empty.
- For each, do a quick sanity check (has files/subdirectories inside).
- Present the valid datasets to the user via AskUserQuestion (multiSelect) and ask which ones to process.

**4b. Understand the model's data format**
- Read the model's training code to understand what data format it expects:
  - Look for dataset classes, data loaders, config files that specify data paths
  - Check existing preprocessing scripts (e.g. `training/data/preprocess/`, `scripts/`)
  - Read the training config to understand expected directory structure
- This informs how to write the conversion scripts.

**4c. Write data preparation scripts**
- For each selected dataset, create `thirdparty/<model>/data_prepare/prepare_<dataset>.py`
- Each script:
  - Takes `--raw <input-dir>` and `--output <output-dir>` arguments
  - Converts the raw dataset into the format expected by the model's training code
  - Prints progress and a summary at the end
  - Is self-contained (uses only dependencies available in the Docker image)

**4d. Run data preparation in container**
- Create the output directory: `mkdir -p <data-path>/processed/<model>`
- For each dataset, run the prep script inside the container:
  ```bash
  docker run --rm --gpus all \
    -v <data-path>:/data \
    -v $(pwd)/thirdparty/<model>:/workspace \
    ghcr.io/wangxinjian1108/<model>:latest \
    bash -c "cd /workspace && python data_prepare/prepare_<dataset>.py \
      --raw /data/raw/<dataset> \
      --output /data/processed/<model>/<dataset>"
  ```
- If a prep script fails, diagnose and fix it on the dev branch, then retry (up to 3 attempts per dataset).

### 5. Closed-loop Training Test (with Dockerfile Update Loop)

**5a. Create training config for test**
- Read the model's existing training config and entry point.
- Write or modify a test config (e.g. `data_prepare/train_test_config.yaml` or similar) that:
  - Points data paths to `/data/processed/<model>/`
  - Sets `max_epochs: 1` (or equivalent)
  - Uses a small batch size suitable for a single GPU
  - Disables unnecessary features (wandb logging, heavy augmentation, etc.) if possible

**5b. Run training (Attempt 1: Current Image)**
```bash
docker run --rm --gpus all --shm-size=4gb \
  -v <data-path>:/data \
  -v $(pwd)/thirdparty/<model>:/workspace \
  ghcr.io/wangxinjian1108/<model>:latest \
  bash -c "cd /workspace && <training-command-with-test-config>"
```
- The training command depends on the model (e.g. for vggt: `python training/launch.py --config train_test`)

**5c. Evaluate result and handle missing dependencies**
- Success = 1 full epoch completes without error (training + validation if applicable).
- If training fails with `ModuleNotFoundError` or `ImportError`:
  a. **Identify missing packages**: Parse error output to extract package names
  b. **Update Dockerfile**: 
     - Locate `docker/<model>/Dockerfile`
     - Add missing packages to the appropriate pip/conda install command
     - Document which packages were added and why
  c. **Update GitHub Actions workflow**:
     - Locate `.github/workflows/docker-<model>.yml`
     - Ensure workflow is configured to rebuild on changes
  d. **Commit and push to master**:
     - `cd thirdparty/<model> && git add -A && git commit -m "fix: add training dependencies"`
     - `git push origin dev` (or merge to master if ready)
     - Return to repo root
     - `git add docker/<model>/Dockerfile .github/workflows/docker-<model>.yml`
     - `git commit -m "chore: update Dockerfile and workflow with training dependencies"`
     - `git push origin master`
  e. **Trigger image rebuild**:
     - Run: `gh workflow run docker-<model>.yml`
     - Wait for workflow to complete (check with `gh run list`)
  f. **Pull new image**:
     - `docker pull ghcr.io/wangxinjian1108/<model>:latest`
  g. **Retry training** with new image (go back to 5b, up to 3 total attempts)
- If training fails with other errors (OOM, data format, config):
  a. Capture and analyze the error output
  b. Fix the issue in the dev branch code (data loading, config, compatibility, etc.)
  c. Commit to dev: `git add -A && git commit -m "fix: <issue>"`
  d. Retry training (up to 3 attempts total)
- If still failing after 3 attempts, stop and report what's broken.

### 6. Commit Dev Branch Changes

After successful training:
- `cd thirdparty/<model>`
- Stage all new/modified files:
  ```
  git add data_prepare/
  git add <any-other-modified-files>
  ```
- Commit: `git commit -m "feat: add data preparation and training test scripts"`
- Push: `git push -u origin dev`
- Return to repo root.

### 7. Final Integration (if training succeeded)

- Merge dev branch to master (or create PR for review)
- Update submodule reference in main repo
- Commit: `git add thirdparty/<model> && git commit -m "chore: update <model> submodule with training pipeline"`
- Push to master

### 8. Report

One paragraph summary:
- Which datasets were processed and their sizes
- Training result: success (1 epoch completed) or failure (what broke)
- What was committed to the dev branch
- If Dockerfile was updated: which dependencies were added and why
- Any issues that need manual attention
