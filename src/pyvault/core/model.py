"""In-memory vault data model and its JSON (de)serialization.

This module deals only with plaintext structures. Encryption lives in
:mod:`pyvault.core.vault_file`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pyvault.errors import VaultCorruptError

MODEL_VERSION = 1


def _now() -> str:
    """Current UTC time as an ISO-8601 string (seconds precision)."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


@dataclass
class Entry:
    """A single stored credential."""

    title: str
    username: str = ""
    password: str = ""
    url: str = ""
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "username": self.username,
            "password": self.password,
            "url": self.url,
            "notes": self.notes,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Entry:
        try:
            return cls(
                id=data["id"],
                title=data["title"],
                username=data.get("username", ""),
                password=data.get("password", ""),
                url=data.get("url", ""),
                notes=data.get("notes", ""),
                tags=list(data.get("tags", [])),
                created_at=data["created_at"],
                updated_at=data["updated_at"],
            )
        except (KeyError, TypeError) as exc:
            raise VaultCorruptError(f"invalid entry: {exc}") from exc


@dataclass
class Vault:
    """A collection of credential entries plus metadata."""

    entries: list[Entry] = field(default_factory=list)
    version: int = MODEL_VERSION
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    # --- queries -------------------------------------------------------
    def get(self, entry_id: str) -> Entry | None:
        return next((e for e in self.entries if e.id == entry_id), None)

    def search(self, query: str) -> list[Entry]:
        """Case-insensitive match against title, username, and url."""
        q = query.strip().lower()
        if not q:
            return list(self.entries)
        return [
            e
            for e in self.entries
            if q in e.title.lower() or q in e.username.lower() or q in e.url.lower()
        ]

    # --- mutations -----------------------------------------------------
    def add(self, entry: Entry) -> Entry:
        self.entries.append(entry)
        self._touch()
        return entry

    def update(self, entry_id: str, **changes: Any) -> Entry:
        entry = self.get(entry_id)
        if entry is None:
            raise KeyError(entry_id)
        for key, value in changes.items():
            if not hasattr(entry, key) or key in {"id", "created_at"}:
                raise AttributeError(f"cannot update field {key!r}")
            setattr(entry, key, value)
        entry.updated_at = _now()
        self._touch()
        return entry

    def delete(self, entry_id: str) -> None:
        entry = self.get(entry_id)
        if entry is None:
            raise KeyError(entry_id)
        self.entries.remove(entry)
        self._touch()

    def _touch(self) -> None:
        self.updated_at = _now()

    # --- serialization -------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Vault:
        try:
            version = int(data["version"])
            if version != MODEL_VERSION:
                raise VaultCorruptError(f"unsupported vault model version: {version}")
            return cls(
                version=version,
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                entries=[Entry.from_dict(e) for e in data["entries"]],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise VaultCorruptError(f"invalid vault contents: {exc}") from exc
