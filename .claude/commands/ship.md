Commit staged/unstaged changes, open a PR to master, then watch the GitHub Actions run and fix failures.

## Argument
`$ARGUMENTS` is an optional commit message. If omitted, generate one from the diff.

## Steps

1. **Sanity check** — run `git status` and `git diff HEAD` to understand what has changed. If there is nothing to commit, report that and stop.

2. **Stage & commit**
   - Stage all tracked modifications: `git add -u`
   - Also stage any new untracked files that are clearly part of the work (e.g. new Dockerfiles, workflow files, source files). Do NOT stage `.env`, secrets, or large binaries.
   - Commit with the provided message, or generate a concise one from the diff if none was given:
     ```
     git commit -m "<message>"
     ```
   - If a pre-commit hook fails, fix the reported issue, re-stage, and create a **new** commit (never use `--no-verify`).

3. **Push & open PR**
   - Push the current branch: `git push -u origin HEAD`
   - Open a PR to `master` with `gh pr create --base master --fill`
   - Print the PR URL.

4. **Watch the CI run**
   - Get the latest run for the PR: `gh pr checks <PR-number> --watch` (polls until all checks finish)
   - If all checks pass → report success and stop.

5. **Fix failures (iterate up to 3 times)**
   If any check fails:
   a. Fetch the failed job logs: `gh run view <run-id> --log-failed`
   b. Analyse the error. Common patterns:
      - Dockerfile build error → fix the relevant Dockerfile
      - Lint / format error → fix the reported file
      - Missing secret → note it for the user, do not retry
      - Flaky network (e.g. download timeout) → retry the run with `gh run rerun <run-id> --failed` without changing code
   c. Apply the fix to the relevant file(s).
   d. Stage the fix and amend the last commit (since the PR is already open, amend keeps the history clean):
      ```
      git add -u
      git commit --amend --no-edit
      git push --force-with-lease
      ```
   e. Wait for the new CI run to finish (go back to step 4).
   f. After 3 failed fix attempts, stop and summarise what is still broken so the user can decide.

6. **Report** — one or two sentences: PR URL, final CI status, and any remaining issues that need manual attention (e.g. secrets that must be configured in the repo settings).
