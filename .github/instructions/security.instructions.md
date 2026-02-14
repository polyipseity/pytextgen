# Security & Secrets Handling

This document covers security best-practices for the repository.

Secrets storage:

- **Never** commit plaintext secrets to the repository. Use an encrypted
  `private.yaml.gpg` or other secure secret storage mechanisms when necessary.
- Store private keys, credentials, and other sensitive material in
  `private.yaml.gpg` (or an external secret manager such as GitHub Secrets for
  CI) and document the decryption workflow in this file.

GPG & signing:

- Use GPG-signed commits for release/version commits and for workflows that
  require an auditable history.
- Configure `user.signingkey` in git config and ensure `gpg` is available in
  CI if signed tags/commits are required in automation steps.

Reporting security issues:

- Report vulnerabilities privately to maintainers. If a `SECURITY.md` exists
  include the contact and escalation steps (email or issue tracker link).
- If an automated agent discovers a potential secret or credential in the repo,
  it must stop further changes, redact the secret from any generated output,
  and notify a human maintainer immediately following the `SECURITY.md` steps.
  Do not attempt to remediate or rotate secrets yourself without express human direction.

Credential scanning:

- Use prek hooks (detect-aws-credentials, detect-private-key) to catch
  accidental commits of credentials prior to pushing. Add or adjust hooks in `prek.toml` or keep `.pre-commit-config.yaml` for compatibility.
