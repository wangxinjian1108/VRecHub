Add a git repo as a submodule, dockerize it, create a GitHub Actions workflow, commit, push, and monitor CI until success.

## Argument
`$ARGUMENTS` is a git SSH URL (e.g. `git@github.com:org/repo-name.git`).

## Steps

1. **Add or update submodule**
   - Extract `<repo-name>` from the SSH URL (last path segment without `.git`)
   - Check if `thirdparty/<repo-name>` already exists in `.gitmodules`:
     - If yes: run `git submodule update --init --remote thirdparty/<repo-name>` to pull the latest commit
     - If no: run `git submodule add <ssh-url> thirdparty/<repo-name>` then `git submodule update --init --recursive thirdparty/<repo-name>`

2. **Dockerize** — invoke the `/dockerize-submodule` skill with `thirdparty/<repo-name>` as the argument. This handles:
   - Detecting project type, Python version, CUDA version
   - Creating the Dockerfile at `docker/<repo-name>/Dockerfile`
   - Asking about Zelos Harbor
   - Creating the GitHub Actions workflow at `.github/workflows/docker-<repo-name>.yml`

3. **Commit & push**
   - Stage: the new/updated submodule, Dockerfile, workflow file, and any modified `.gitmodules`
   - Do NOT stage `.env`, `config/token.yaml`, secrets, or large binaries
   - Commit with message: `feat: add <repo-name> Dockerfile and workflow`
   - Push to master: `git push`

4. **Monitor CI (iterate up to 3 times on failure)**
   - Find the triggered workflow run for `Docker – <repo-name>`
   - Wait for it to complete
   - If success → report and stop
   - If failure:
     a. Fetch logs: `gh run view <run-id> --log-failed`
     b. Diagnose and fix the issue
     c. Amend commit and force-push: `git add -u && git commit --amend --no-edit && git push --force-with-lease`
     d. Wait for new run
   - After 3 failed attempts, stop and report what's broken

5. **Update image list** — invoke the `/list-images` skill to regenerate `IMAGES.md` with the new image included. Then stage and amend the last commit:
   ```
   git add IMAGES.md && git commit --amend --no-edit && git push --force-with-lease
   ```

6. **Report** — one sentence: workflow status and image name (e.g. `ghcr.io/wangxinjian1108/<repo-name>:latest`)
