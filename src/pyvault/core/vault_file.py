"""On-disk encrypted vault format and safe file I/O.

Envelope layout (a small JSON header wrapping the ciphertext)::

    {
      "magic": "PYVAULT",
      "format": 1,
      "kdf": { ...Argon2id params... },
      "cipher": "AES-256-GCM",
      "nonce": "<base64>",
      "ciphertext": "<base64>"      # AES-256-GCM(vault-json), tag appended
    }

Only the encrypted ``ciphertext`` contains secrets. The header fields are
authenticated as GCM associated data (AAD), so an attacker cannot swap the
salt/params or downgrade the format without decryption failing.

Writes are atomic (temp file + fsync + ``os.replace``) and the previous good
vault is preserved as a ``.bak`` sibling, so a crash or a cloud-sync race can
never leave a half-written or destroyed vault.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyvault.core.model import Vault
from pyvault.crypto import cipher
from pyvault.crypto.kdf import KdfParams, derive_key
from pyvault.errors import VaultCorruptError, VaultVersionError

MAGIC = "PYVAULT"
FORMAT_VERSION = 1
CIPHER_NAME = "AES-256-GCM"


@dataclass
class LoadedVault:
    """An unlocked vault plus what's needed to re-encrypt and save it."""

    vault: Vault
    key: bytes
    kdf_params: KdfParams


def _aad(kdf_params: KdfParams) -> bytes:
    """Associated data binding the header to the ciphertext.

    Serialized canonically (sorted keys) so encrypt and decrypt agree byte-for-byte.
    """
    header = {
        "magic": MAGIC,
        "format": FORMAT_VERSION,
        "cipher": CIPHER_NAME,
        "kdf": kdf_params.to_dict(),
    }
    return json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _serialize(vault: Vault, key: bytes, kdf_params: KdfParams) -> bytes:
    plaintext = json.dumps(vault.to_dict(), separators=(",", ":")).encode("utf-8")
    nonce, ciphertext = cipher.encrypt(key, plaintext, aad=_aad(kdf_params))
    envelope = {
        "magic": MAGIC,
        "format": FORMAT_VERSION,
        "cipher": CIPHER_NAME,
        "kdf": kdf_params.to_dict(),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    return json.dumps(envelope, indent=2).encode("utf-8")


def _parse_envelope(raw: bytes) -> dict[str, Any]:
    try:
        envelope = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise VaultCorruptError(f"vault file is not valid JSON: {exc}") from exc
    if not isinstance(envelope, dict):
        raise VaultCorruptError("vault file has an unexpected structure")
    if envelope.get("magic") != MAGIC:
        raise VaultCorruptError("not a PyVault file (bad magic marker)")
    fmt = envelope.get("format")
    if fmt != FORMAT_VERSION:
        raise VaultVersionError(f"unsupported vault format version: {fmt!r}")
    return envelope


def _atomic_write(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` atomically, backing up any existing file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)  # atomic on POSIX and Windows


# --- public API --------------------------------------------------------


def save_vault(path: str | os.PathLike[str], loaded: LoadedVault) -> None:
    """Encrypt and atomically persist an unlocked vault."""
    data = _serialize(loaded.vault, loaded.key, loaded.kdf_params)
    _atomic_write(Path(path), data)


def create_vault(
    path: str | os.PathLike[str],
    password: str,
    *,
    kdf_params: KdfParams | None = None,
) -> LoadedVault:
    """Create, save, and return a new empty vault at ``path``.

    ``kdf_params`` may be supplied to override the (deliberately heavy) defaults,
    primarily so tests can run quickly.
    """
    params = kdf_params or KdfParams.create()
    key = derive_key(password, params)
    loaded = LoadedVault(vault=Vault(), key=key, kdf_params=params)
    save_vault(path, loaded)
    return loaded


def open_vault(path: str | os.PathLike[str], password: str) -> LoadedVault:
    """Read, decrypt, and return the vault at ``path``.

    Raises :class:`~pyvault.errors.InvalidPasswordError` on a wrong password or
    tampering, and :class:`~pyvault.errors.VaultCorruptError` on a malformed file.
    """
    raw = Path(path).read_bytes()
    envelope = _parse_envelope(raw)
    kdf_params = KdfParams.from_dict(envelope["kdf"])
    try:
        nonce = base64.b64decode(envelope["nonce"])
        ciphertext = base64.b64decode(envelope["ciphertext"])
    except (KeyError, ValueError, TypeError) as exc:
        raise VaultCorruptError(f"invalid vault envelope: {exc}") from exc

    key = derive_key(password, kdf_params)
    plaintext = cipher.decrypt(key, nonce, ciphertext, aad=_aad(kdf_params))
    try:
        vault_data = json.loads(plaintext)
    except json.JSONDecodeError as exc:
        raise VaultCorruptError(f"decrypted vault is not valid JSON: {exc}") from exc
    return LoadedVault(vault=Vault.from_dict(vault_data), key=key, kdf_params=kdf_params)
