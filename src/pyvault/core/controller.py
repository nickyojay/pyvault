"""GUI-agnostic vault session controller.

This is the single seam the UI talks to. It owns the open vault, performs every
mutation through the core model, and persists after each change. It contains no
Qt (or any UI) imports, so it is fully unit-testable headless.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

from pyvault.core.model import Entry, Vault
from pyvault.core.portability import export_csv, import_csv
from pyvault.core.vault_file import (
    LoadedVault,
    create_vault,
    open_vault,
    save_vault,
)
from pyvault.crypto.kdf import KdfParams, derive_key
from pyvault.errors import InvalidPasswordError, VaultError


class VaultController:
    """Manages one vault: create/unlock/lock and CRUD with auto-save."""

    def __init__(self, vault_path: str | os.PathLike[str], *, kdf_params: KdfParams | None = None):
        self._path = Path(vault_path)
        self._kdf_params = kdf_params
        self._loaded: LoadedVault | None = None
        self._synced_mtime: int | None = None
        #: Path of the most recent preserved sync-conflict copy (UI reads + clears).
        self.last_conflict_path: Path | None = None

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
        self._mark_synced()

    def unlock(self, password: str) -> None:
        self._loaded = open_vault(self._path, password)
        self._mark_synced()

    def lock(self) -> None:
        self._loaded = None
        self._synced_mtime = None

    def change_password(self, current: str, new: str) -> None:
        """Re-encrypt the vault under a new master password.

        Verifies ``current`` against the open vault, then derives a fresh key
        from a new random salt (reusing the current cost parameters) and saves.
        """
        loaded = self._require_loaded()
        if derive_key(current, loaded.kdf_params) != loaded.key:
            raise InvalidPasswordError("current master password is incorrect")
        cur = loaded.kdf_params
        new_params = KdfParams.create(
            time_cost=cur.time_cost,
            memory_cost=cur.memory_cost,
            parallelism=cur.parallelism,
        )
        new_key = derive_key(new, new_params)
        self._loaded = LoadedVault(vault=loaded.vault, key=new_key, kdf_params=new_params)
        self._save()

    # --- queries -------------------------------------------------------
    def _require_loaded(self) -> LoadedVault:
        if self._loaded is None:
            raise VaultError("vault is locked")
        return self._loaded

    @property
    def _vault(self) -> Vault:
        return self._require_loaded().vault

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

    # --- import / export ----------------------------------------------
    def export_csv(self, path: str | os.PathLike[str]) -> None:
        export_csv(self._vault.entries, path)

    def import_csv(self, path: str | os.PathLike[str]) -> int:
        """Import entries from a CSV file. Returns the number added."""
        imported = import_csv(path)
        for entry in imported:
            self._vault.add(entry)
        if imported:
            self._save()
        return len(imported)

    # --- persistence + sync-conflict handling -------------------------
    def _disk_mtime(self) -> int | None:
        try:
            return self._path.stat().st_mtime_ns
        except FileNotFoundError:
            return None

    def _mark_synced(self) -> None:
        self._synced_mtime = self._disk_mtime()

    def _save(self) -> None:
        loaded = self._require_loaded()
        # If the file changed underneath us (e.g. a cloud client synced a copy
        # from another device), preserve that version before we overwrite it so
        # nothing is silently lost. The user can merge from the conflict file.
        if self._path.exists() and self._disk_mtime() != self._synced_mtime:
            self.last_conflict_path = self._preserve_conflict()
        save_vault(self._path, loaded)
        self._mark_synced()

    def _preserve_conflict(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        conflict = self._path.with_name(f"{self._path.stem}.conflict-{stamp}{self._path.suffix}")
        shutil.copy2(self._path, conflict)
        return conflict
