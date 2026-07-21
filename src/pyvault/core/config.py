"""Application settings (non-secret) persisted as JSON.

Only preferences live here — never the master password or vault contents. The
default location is ``~/.pyvault/config.json``; the vault itself defaults to a
sibling ``vault.vault`` that the user can repoint at a cloud-synced folder.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

CONFIG_DIR = Path.home() / ".pyvault"
CONFIG_PATH = CONFIG_DIR / "config.json"
DEFAULT_VAULT_PATH = CONFIG_DIR / "vault.vault"


@dataclass
class Config:
    """User preferences for the app."""

    vault_path: str = str(DEFAULT_VAULT_PATH)
    auto_lock_minutes: int = 5
    clipboard_clear_seconds: int = 15

    @classmethod
    def load(cls, path: str | Path = CONFIG_PATH) -> Config:
        """Load config, falling back to defaults for missing/invalid files."""
        p = Path(path)
        if not p.exists():
            return cls()
        try:
            data = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self, path: str | Path = CONFIG_PATH) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=2))
