"""Argon2id key derivation for the master password.

The derived key never leaves memory and is never written to disk. Only the
(non-secret) KDF parameters and salt are persisted in the vault header so the
file stays portable across machines.
"""

from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass
from typing import Any

from argon2.low_level import Type, hash_secret_raw

from pyvault.errors import VaultCorruptError

ALGO = "argon2id"
KEY_LEN = 32  # 256-bit key for AES-256
SALT_LEN = 16

# Defaults follow OWASP guidance for Argon2id (memory-hard). memory_cost is in
# KiB, so 262144 KiB = 256 MiB.
DEFAULT_TIME_COST = 3
DEFAULT_MEMORY_COST = 262144
DEFAULT_PARALLELISM = 4


@dataclass(frozen=True)
class KdfParams:
    """Parameters needed to reproduce the key from the master password."""

    salt: bytes
    time_cost: int = DEFAULT_TIME_COST
    memory_cost: int = DEFAULT_MEMORY_COST
    parallelism: int = DEFAULT_PARALLELISM
    algo: str = ALGO

    @classmethod
    def create(
        cls,
        *,
        time_cost: int = DEFAULT_TIME_COST,
        memory_cost: int = DEFAULT_MEMORY_COST,
        parallelism: int = DEFAULT_PARALLELISM,
    ) -> KdfParams:
        """Build fresh params with a cryptographically random salt."""
        return cls(
            salt=secrets.token_bytes(SALT_LEN),
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "algo": self.algo,
            "salt": base64.b64encode(self.salt).decode("ascii"),
            "time_cost": self.time_cost,
            "memory_cost": self.memory_cost,
            "parallelism": self.parallelism,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KdfParams:
        try:
            algo = data["algo"]
            if algo != ALGO:
                raise VaultCorruptError(f"unsupported KDF algorithm: {algo!r}")
            return cls(
                salt=base64.b64decode(data["salt"]),
                time_cost=int(data["time_cost"]),
                memory_cost=int(data["memory_cost"]),
                parallelism=int(data["parallelism"]),
                algo=algo,
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise VaultCorruptError(f"invalid KDF parameters: {exc}") from exc


def derive_key(password: str, params: KdfParams) -> bytes:
    """Derive a 32-byte key from the master password and KDF parameters."""
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=params.salt,
        time_cost=params.time_cost,
        memory_cost=params.memory_cost,
        parallelism=params.parallelism,
        hash_len=KEY_LEN,
        type=Type.ID,
    )
