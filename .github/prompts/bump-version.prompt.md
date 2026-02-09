---
name: bump-version
description: Bump the project version (MAJOR | MINOR | PATCH), update files, and create a signed release commit and tag by default.
argument-hint: Required `part=major|minor|patch`. Optional `commitNow=no` to skip committing; `tag=no` to skip tagging; `push=no` to skip pushing.
agent: agent
---

<!-- markdownlint-disable-file MD013 MD036 -->

# Bump Version

**Never ask for confirmation or clarification. Always proceed automatically using best-effort defaults and available context.**

## Workflow

1. **Read current versions**
   - Print the current canonical version from `pyproject.toml` and search the repository for a source file that defines a `VERSION` variable (e.g., `src/<pkg>/__init__.py` or `<pkg>/__init__.py`). Example (one-liners):

     ```shell
     python - <<'PY'
     import tomllib,sys,glob,re
     data = tomllib.loads(open('pyproject.toml','rb').read())
     print('pyproject:', data['project']['version'])
     candidates = glob.glob('src/*/__init__.py') + glob.glob('*/*/__init__.py') + glob.glob('*/__init__.py')
     for p in candidates:
         s = open(p,'r',encoding='utf-8').read()
         m = re.search(r'^VERSION\s*=\s*["\'](.*)["\']', s, re.M)
         if m:
             print(p + ':', m.group(1))
             break
     else:
         print('package_version: not found')
         sys.exit(2)
     PY
     ```

   - If the two versions do not match exactly, stop and report the mismatch (do not attempt an automated fix).

2. **Determine new version**
   - Require `${input:part}` to be one of `major`, `minor`, or `patch`. Use semantic versioning: MAJOR.MINOR.PATCH (pre-release/build metadata not supported by this prompt).
   - Compute the new version by incrementing the requested part and zeroing lower-order parts. Examples:
     - `major`: 1.2.3 -> 2.0.0
     - `minor`: 1.2.3 -> 1.3.0
     - `patch`: 1.2.3 -> 1.2.4
   - If the current version does not match the simple `X.Y.Z` pattern, abort with a clear error message.

3. **Update files**
   - Update `pyproject.toml` `[project].version` to the new version.
   - Update the discovered source file's `VERSION = "..."` to the new version. Preserve formatting and comments.

4. **Synchronize lockfile (recommended)**
   - Run `uv sync --all-extras --dev` to refresh `uv.lock` and development extras.
   - If `uv.lock` changed, include it in the release commit.

5. **Run quick validation (recommended)**
   - Run tests and linting: `uv run pytest` and `uv run ruff check --fix .` (best-effort; do not block the release on transient failures — report failures in output).

6. **Create release commit**
   - Stage changed files: `pyproject.toml`, the discovered source file (e.g., `src/<pkg>/__init__.py`), and `uv.lock` (if modified).
   - Commit using the new version string as the commit message and sign the commit with GPG.

     - **PowerShell (Windows)**:

       ```powershell
       git add pyproject.toml <source_file> uv.lock
       git commit -S -m "${new_version}"
       git rev-parse HEAD
       ```

     - **Bash/zsh (Linux/macOS)**:

       ```bash
       git add pyproject.toml <source_file> uv.lock
       git commit -S -m "${new_version}"
       git rev-parse HEAD
       ```

   - If `${input:commitNow}` is `no`, skip creating the commit and only show the intended commit message and diff of changes.

7. **Create signed annotated tag (optional)**
   - Unless `${input:tag}` is `no`, create a signed annotated tag `v${new_version}` with message `v${new_version}`.

     ```powershell
     git tag -s -a v${new_version} -m "v${new_version}"
     ```

8. **Push (optional)**
   - Unless `${input:push}` is `no`, push the release commit and tags:

     ```powershell
     git push origin HEAD && git push origin --tags
     ```

9. **Output**
   - A brief summary: previous version, new version, files changed, whether `uv.lock` was updated, commit SHA (if created), and tag (if created).
   - Include the exact commands that were run and any relevant command output.

## Rules

- Never ask for confirmation or clarification. Always proceed automatically using best-effort defaults and available context.
- Only modify the version in `pyproject.toml` and the discovered source file defining `VERSION`. Update `uv.lock` only via `uv sync` and include it if changed.
- Require `${input:part}` to be `major`, `minor`, or `patch`; do not infer the part from the user-provided text.
- Use the new version string as the commit message and create a signed commit as described above.
- If any step fails due to unexpected file formats, invalid version patterns, or GPG signing errors, stop and report the exact error and commands attempted.

## Inputs

- `${input:part}` — required; one of `major`, `minor`, `patch` (no other values)
- `${input:commitNow}` — optional; `no` to skip committing (default: commit)
- `${input:tag}` — optional; `no` to skip creating a signed tag (default: create tag)
- `${input:push}` — optional; `no` to skip `git push` (default: push)

End of prompt.
