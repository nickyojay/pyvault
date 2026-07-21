# PyVault

A simple, secure, cross-platform (Windows / macOS / Linux) personal password manager.

- **GUI:** PySide6 (Qt for Python)
- **Storage:** a single encrypted vault file you can place in a cloud-synced folder (Dropbox / iCloud / Drive) for automatic sync — no server required.
- **Crypto:** Argon2id key derivation + AES-256-GCM authenticated encryption. Only the encrypted blob ever touches disk.

> ⚠️ Personal-use project. See [`docs/security.md`](docs/security.md) for the threat model and known limitations.

## Project status

Phase 0 (scaffold) complete. See the roadmap below.

| Phase | Goal | Status |
|-------|------|--------|
| 0 | Scaffold: layout, deps, tooling, CI | ✅ |
| 1 | Crypto core (KDF, AES-GCM, vault file I/O) + tests | ⬜ |
| 2 | Temporary CLI harness to exercise the core | ⬜ |
| 3 | PySide6 GUI (unlock, entry list, editor, generator) | ⬜ |
| 4 | Hardening & UX (auto-lock, clipboard clear, change master password) | ⬜ |
| 5 | Packaging (PyInstaller) + security docs | ⬜ |

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Common commands

```bash
pytest            # run tests
ruff check .      # lint
black .           # format
```

## Layout

```
src/pyvault/
  crypto/   # KDF + authenticated encryption
  core/     # vault model, serialization, atomic file I/O
  ui/       # PySide6 GUI
  cli.py    # temporary command-line harness (Phase 2)
tests/      # unit tests (crypto & I/O first)
```
