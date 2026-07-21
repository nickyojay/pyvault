# Changelog

All notable changes to PyVault are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## [0.1.0] — unreleased

First functional release: a simple, secure, cross-platform personal password
manager.

### Security
- Master password key derivation with **Argon2id** (random per-vault salt,
  OWASP-tuned cost parameters).
- Vault encrypted with **AES-256-GCM**; the file header is authenticated as
  associated data. Only ciphertext is written to disk.
- Atomic writes (temp + fsync + replace) with a rolling `.bak`.
- Sync-conflict preservation: an externally-modified vault is backed up before
  overwrite so nothing is lost.
- Auto-lock on inactivity and clipboard auto-clear.

### Features
- **Desktop GUI** (PySide6): unlock/create, searchable entry list, add/edit,
  password generator, settings.
- **Security audit**: offline weak/reused detection plus an opt-in Have I Been
  Pwned breach check using k-anonymity (only a 5-char hash prefix is sent).
- Change master password; CSV import (Chrome/Firefox/etc.) and export.
- Password strength hint on the master password and stored entries.
- **CLI** (`pyvault`): `init`, `add`, `list`, `get`, `rm`, `gen`, `passwd`,
  `import`, `export`, `audit`.

### Packaging
- Standalone single-file builds for Windows, macOS, and Linux via PyInstaller.
- CI test matrix (win/mac/linux × py3.11/3.12) and release build workflow.
