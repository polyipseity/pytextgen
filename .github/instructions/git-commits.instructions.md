<!-- markdownlint-disable-file MD013 MD036 -->

# Git Commit & Commit Message Conventions

This file documents the repository's expectations for commit messages, signing,
and release commits.

Conventional commits:

- Use the Conventional Commit format (`type(scope): short description`).
  Example: `chore(tests): add async file factory fixture`.

Commit body & wrapping:

- Wrap commit body lines to **72 characters** or fewer. Use 72 as a buffer for
  human-readability. Note: some tooling (commitlint, editor helpers) may still
  be configured for 100 characters—if those tools reject a commit, rewrap to
  satisfy the tool but prefer 72 where possible.

Signed release commits & tags:

- Release commits that bump the package version MUST be signed with GPG.
  Example steps:

    ```powershell
    git add pytextgen/__init__.py
    git commit -S -m "1.2.3"
    git tag -s -a v1.2.3 -m "v1.2.3"
    git push origin HEAD && git push origin --tags
    ```

Pre-commit & validation:

- Run `prek run --all-files` locally before pushing changes.
- Ensure tests and linters pass; CI will re-run these and block the PR if they fail.

Agent & automation notes:

- Agents must include a short rationale in the commit body when deviating from
  usual conventions or performing non-trivial changes.
- Agents must run the same local checks documented in `.github/instructions/agents.instructions.md` before committing (format, pyright, tests, and prek hooks). If unsure about a behavioural change, stop and ask a maintainer rather than guessing — include the question and context in the PR body.
- Domain-data or transaction commits (if applicable) may follow stricter
  machine-parseable formats; follow domain-specific policies if present.
