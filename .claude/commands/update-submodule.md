Update an existing submodule to its latest upstream commit and rebuild its Docker image.

## Argument
`$ARGUMENTS` is the submodule name or path (e.g. `Scal3R` or `thirdparty/Scal3R`).

## Steps

1. **Locate the submodule** — search `.gitmodules` to resolve the full path if only a name was given. Verify the submodule directory exists.

2. **Update to latest** — pull the latest commit from the submodule's tracked branch:
   ```
   git submodule update --init --remote thirdparty/<repo-name>
   ```

3. **Check for changes** — run `git diff --submodule thirdparty/<repo-name>` to confirm the submodule pointer moved. If nothing changed, report "already up to date" and stop.

4. **Rebuild image (optional)** — use AskUserQuestion to ask whether to also rebuild the Docker image. If yes:
   - Check if `docker/<repo-name>/Dockerfile` exists. If not, suggest running `/dockerize-submodule` first.
   - Trigger the workflow manually: `gh workflow run docker-<repo-name>.yml`
   - Or, if the user prefers, commit and push to trigger it via the paths filter.

5. **Commit & push**
   - Stage the submodule pointer change: `git add thirdparty/<repo-name>`
   - Commit: `feat: update <repo-name> to latest`
   - Push: `git push`

6. **Monitor CI** — if a workflow was triggered:
   - Wait for the run to complete
   - If success → report and stop
   - If failure:
     a. Fetch logs: `gh run view <run-id> --log-failed`
     b. If the failure is in the Dockerfile (e.g. new dependency missing), fix it, amend, and force-push
     c. Iterate up to 3 times
   - After 3 failed attempts, stop and report

7. **Report** — one sentence: new submodule commit hash and CI status.
