"""GUI-agnostic vault session controller.

This is the single seam the UI talks to. It owns the open vault, performs every
mutation through the core model, and persists after each change. It contains no
Qt (or any UI) imports, so it is fully unit-testable headless.
"""

from __future__ import annotations

import os
from pathlib import Path

from pyvault.core.model import Entry, Vault
from pyvault.core.vault_file import (
    LoadedVault,
    create_vault,
    open_vault,
    save_vault,
)
from pyvault.crypto.kdf import KdfParams
from pyvault.errors import VaultError


class VaultController:
    """Manages one vault: create/unlock/lock and CRUD with auto-save."""

    def __init__(self, vault_path: str | os.PathLike[str], *, kdf_params: KdfParams | None = None):
        self._path = Path(vault_path)
        self._kdf_params = kdf_params
        self._loaded: LoadedVault | None = None

    # --- state ---------------------------------------------------------
    @property
    def path(self) -> Path:
        return self._path

    def set_path(self, path: str | os.PathLike[str]) -> None:
        """Point at a different vault file. Locks any currently open vault."""
        self.lock()
        self._path = Path(path)

    @property
    def is_unlocked(self) -> bool:
        return self._loaded is not None

    def vault_exists(self) -> bool:
        return self._path.exists()

    # --- lifecycle -----------------------------------------------------
    def create(self, password: str) -> None:
        if self._path.exists():
            raise VaultError(f"a vault already exists at {self._path}")
        self._loaded = create_vault(self._path, password, kdf_params=self._kdf_params)

    def unlock(self, password: str) -> None:
        self._loaded = open_vault(self._path, password)

    def lock(self) -> None:
        self._loaded = None

    # --- queries -------------------------------------------------------
    @property
    def _vault(self) -> Vault:
        if self._loaded is None:
            raise VaultError("vault is locked")
        return self._loaded.vault

    def entries(self) -> list[Entry]:
        return list(self._vault.entries)

    def search(self, query: str) -> list[Entry]:
        return self._vault.search(query)

    def get(self, entry_id: str) -> Entry | None:
        return self._vault.get(entry_id)

    # --- mutations (auto-saving) --------------------------------------
    def add_entry(
        self,
        *,
        title: str,
        username: str = "",
        password: str = "",
        url: str = "",
        notes: str = "",
    ) -> Entry:
        entry = self._vault.add(
            Entry(title=title, username=username, password=password, url=url, notes=notes)
        )
        self._save()
        return entry

    def update_entry(self, entry_id: str, **changes: object) -> Entry:
        entry = self._vault.update(entry_id, **changes)
        self._save()
        return entry

    def delete_entry(self, entry_id: str) -> None:
        self._vault.delete(entry_id)
        self._save()

    def _save(self) -> None:
        if self._loaded is None:
            raise VaultError("vault is locked")
        save_vault(self._path, self._loaded)
