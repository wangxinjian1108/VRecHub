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

### 5. Closed-loop Training Test (with Local Debug → Dockerfile Update → CI/CD Rebuild)

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

**5c. Evaluate result and handle missing dependencies (Local Debug Loop)**
- Success = 1 full epoch completes without error (training + validation if applicable).
- If training fails with `ModuleNotFoundError` or `ImportError`:
  
  **Phase 1: Local Debug (Fast Iteration)**
  a. **Identify missing packages**: Parse error output to extract package names
  b. **Create debug container** with interactive shell:
     ```bash
     docker run -it --gpus all --shm-size=4gb \
       -v <data-path>:/data \
       -v $(pwd)/thirdparty/<model>:/workspace \
       ghcr.io/wangxinjian1108/<model>:latest \
       bash
     ```
  c. **Install missing packages** inside container:
     - For conda-based images: `conda install -c conda-forge <package> -y`
     - For pip-based: `pip install <package>`
     - Test that training now works
  d. **Commit debug changes** to a temporary image:
     ```bash
     docker commit <container-id> ghcr.io/wangxinjian1108/<model>:debug
     ```
  e. **Verify training works** with debug image:
     ```bash
     docker run --rm --gpus all --shm-size=4gb \
       -v <data-path>:/data \
       -v $(pwd)/thirdparty/<model>:/workspace \
       ghcr.io/wangxinjian1108/<model>:debug \
       bash -c "cd /workspace && <training-command-with-test-config>"
     ```
  f. **If training succeeds**, proceed to Phase 2. If fails, go back to step c.
  
  **Phase 2: Formalize Dockerfile (After Debug Success)**
  a. **Update Dockerfile**:
     - Locate `docker/<model>/Dockerfile`
     - Add missing packages to the appropriate pip/conda install command
     - Document which packages were added and why
  b. **Update GitHub Actions workflow**:
     - Locate `.github/workflows/docker-<model>.yml`
     - Ensure workflow is configured to rebuild on changes
  c. **Commit and push to master**:
     - Return to repo root
     - `git add docker/<model>/Dockerfile .github/workflows/docker-<model>.yml`
     - `git commit -m "chore: update Dockerfile with training dependencies"`
     - `git push origin master`
  d. **Trigger image rebuild**:
     - Run: `gh workflow run docker-<model>.yml`
     - Wait for workflow to complete (check with `gh run list`)
  
  **Phase 3: Verify CI/CD Built Image (Final Validation)**
  a. **Pull newly built image**:
     ```bash
     docker pull ghcr.io/wangxinjian1108/<model>:latest
     ```
  b. **Run training with new image** to confirm CI/CD build is correct:
     ```bash
     docker run --rm --gpus all --shm-size=4gb \
       -v <data-path>:/data \
       -v $(pwd)/thirdparty/<model>:/workspace \
       ghcr.io/wangxinjian1108/<model>:latest \
       bash -c "cd /workspace && <training-command-with-test-config>"
     ```
  c. **If successful**, proceed to step 6. If fails, debug and go back to Phase 2.

- If training fails with other errors (OOM, data format, config):
  a. Capture and analyze the error output
  b. Fix the issue in the dev branch code (data loading, config, compatibility, etc.)
  c. Commit to dev: `git add -A && git commit -m "fix: <issue>"`
  d. Retry training (up to 3 attempts total)
- If still failing after 3 attempts, stop and report what's broken.

### 6. Commit Dev Branch Changes

After successful training (with CI/CD built image):
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
- If Dockerfile was updated: which dependencies were added and why (with rationale)
- Confirmation that training works with both debug image and CI/CD built image
- Any issues that need manual attention
