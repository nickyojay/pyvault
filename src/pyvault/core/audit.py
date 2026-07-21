"""Offline vault health checks: reused and weak passwords.

Purely local — nothing leaves the machine. Online breach checking lives in
:mod:`pyvault.core.breach` and is combined with these results by the UI/CLI.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from pyvault.core.model import Entry
from pyvault.core.strength import WEAK, password_strength


@dataclass
class AuditRow:
    """Per-entry audit findings. ``pwned`` is ``None`` until an online check runs."""

    entry: Entry
    weak: bool
    reused: bool
    pwned: int | None = None

    @property
    def has_issue(self) -> bool:
        return self.weak or self.reused or bool(self.pwned)


def reused_passwords(entries: list[Entry]) -> set[str]:
    """Return the set of (non-empty) passwords used by more than one entry."""
    counts = Counter(e.password for e in entries if e.password)
    return {password for password, n in counts.items() if n > 1}


def offline_rows(entries: list[Entry]) -> list[AuditRow]:
    """Build audit rows with weak/reused flags set (breach check not yet run)."""
    reused = reused_passwords(entries)
    rows = []
    for entry in entries:
        weak = bool(entry.password) and password_strength(entry.password) == WEAK
        rows.append(AuditRow(entry=entry, weak=weak, reused=entry.password in reused))
    return rows
