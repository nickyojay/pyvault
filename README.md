# PyVault

A simple, secure, cross-platform (Windows / macOS / Linux) personal password manager.

- **GUI:** PySide6 (Qt for Python)
- **Storage:** a single encrypted vault file you can place in a cloud-synced folder (Dropbox / iCloud / Drive) for automatic sync — no server required.
- **Crypto:** Argon2id key derivation + AES-256-GCM authenticated encryption. Only the encrypted blob ever touches disk.

> ⚠️ Personal-use project. See [`docs/security.md`](docs/security.md) for the threat model and known limitations.

## Project status

Phase 4 (hardening & UX) complete. See the roadmap below.

| Phase | Goal | Status |
|-------|------|--------|
| 0 | Scaffold: layout, deps, tooling, CI | ✅ |
| 1 | Crypto core (KDF, AES-GCM, vault file I/O) + tests | ✅ |
| 2 | CLI harness (init/add/list/get/rm/gen) + generator | ✅ |
| 3 | PySide6 GUI (unlock, entry list, editor, generator, settings) | ✅ |
| 4 | Change master password, CSV import/export, sync-conflict safety, strength hint | ✅ |
| 4.5 | Security audit: weak/reused (offline) + HIBP breach check (k-anonymity) | ✅ |
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

## Desktop app (Phase 3)

```bash
pyvault-gui      # launch the PySide6 desktop app
```

On first run it prompts you to create a master password; after that it shows the
unlock screen. The main window has a searchable entry list, an add/edit form, a
built-in password generator, copy-to-clipboard with auto-clear, a **Lock**
button, and **Settings** (vault file location + auto-lock timeout). Point the
vault path at a cloud-synced folder to sync across machines.

## CLI usage (Phase 2)

The vault path resolves as `--vault PATH` > `$PYVAULT_VAULT` > `~/.pyvault/vault.vault`.

```bash
pyvault init                                   # create a new encrypted vault
pyvault add GitHub -u nick --url https://gh.com -g   # add, generating a password
pyvault list                                   # list entries
pyvault get GitHub --show                       # reveal one entry
pyvault rm GitHub                              # delete an entry
pyvault gen -l 24 --no-ambiguous               # just generate a password
pyvault passwd                                 # change the master password
pyvault export backup.csv                       # export (PLAINTEXT — handle with care)
pyvault import from-chrome.csv                  # import from another manager
pyvault audit                                  # find weak/reused passwords (offline)
pyvault audit --online                          # also check Have I Been Pwned (k-anonymity)
```

### Breach checking & privacy

`audit --online` (and the GUI's **Vault → Security Audit**) checks passwords
against [Have I Been Pwned](https://haveibeenpwned.com/Passwords) using
**k-anonymity**: only the first 5 characters of each password's SHA-1 hash are
sent, so your passwords never leave your machine. Offline weak/reused detection
sends nothing at all.

## Layout

```
src/pyvault/
  crypto/   # KDF + authenticated encryption
  core/     # vault model, serialization, atomic file I/O
  ui/       # PySide6 GUI
  cli.py    # temporary command-line harness (Phase 2)
tests/      # unit tests (crypto & I/O first)
```
