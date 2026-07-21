"""Core vault: data model, serialization, and atomic file I/O."""

from pyvault.core.model import Entry, Vault
from pyvault.core.vault_file import (
    LoadedVault,
    create_vault,
    open_vault,
    save_vault,
)

__all__ = [
    "Entry",
    "Vault",
    "LoadedVault",
    "create_vault",
    "open_vault",
    "save_vault",
]
