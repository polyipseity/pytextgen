---
name: Releases
description: Release checklist and best practices for publishing new versions.
---

# Releases

This document describes a minimal, reproducible release process for `pytextgen`.

## Versioning

- Use semantic versioning (MAJOR.MINOR.PATCH).
- Update the canonical version in `pytextgen/__init__.py` only.

## Release checklist

1. Update `pytextgen/__init__.py` with the new version string (for example, `1.2.3`). Commit only this file in the release commit.

2. Commit using the version string as the commit message and sign the commit with GPG:

```powershell
git add pytextgen/__init__.py
git commit -S -m "1.2.3"
```

3. Create a signed annotated tag:

```powershell
git tag -s -a v1.2.3 -m "v1.2.3"
```

4. Push the release commit and the tag:

```powershell
git push origin HEAD
git push origin --tags
```

5. Build artifacts and publish (CI can handle packaging and publishing; use a manual flow only when needed):

```powershell
uv run --locked -m build
uv run --locked -m twine upload dist/*
```

## Release notes

- If release notes are required, add them in a separate commit and reference them from the release tag or the repository release page.

## CI & automation

- Prefer publishing from CI using stored secrets (PyPI API tokens in CI secrets) and secure workflows.
- Ensure the CI job performs the following checks before publishing: tests, linters, and package build.

## Post-release

- Update any downstream references or submodules if applicable.
- Verify release artifacts are available on the package index and that checksum verification passes.
