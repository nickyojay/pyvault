"""Authenticated encryption with AES-256-GCM.

A fresh random 96-bit nonce is generated for every encryption. The GCM
authentication tag (appended to the ciphertext by the library) provides tamper
detection: any modification to the ciphertext, nonce, or associated data causes
decryption to fail rather than return corrupted plaintext.
"""

from __future__ import annotations

import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from pyvault.errors import InvalidPasswordError

NONCE_LEN = 12  # 96-bit nonce, the standard/optimal size for GCM


def encrypt(key: bytes, plaintext: bytes, aad: bytes | None = None) -> tuple[bytes, bytes]:
    """Encrypt ``plaintext`` and return ``(nonce, ciphertext)``.

    ``ciphertext`` includes the GCM authentication tag. ``aad`` (associated
    data) is authenticated but not encrypted; it must match on decryption.
    """
    nonce = secrets.token_bytes(NONCE_LEN)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    return nonce, ciphertext


def decrypt(key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes | None = None) -> bytes:
    """Decrypt and authenticate ``ciphertext``.

    Raises :class:`InvalidPasswordError` if authentication fails, which happens
    when the key is wrong (wrong master password) or the data was tampered with.
    """
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:
        raise InvalidPasswordError(
            "invalid master password or the vault has been modified"
        ) from exc
