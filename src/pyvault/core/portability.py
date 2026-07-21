"""CSV import/export for migrating to and from other password managers.

CSV is the common interchange format (Chrome, Firefox, Bitwarden, …). Column
headers vary, so import maps a range of aliases onto our fields. Exported files
contain **plaintext passwords** — callers must warn the user.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

from pyvault.core.model import Entry
from pyvault.errors import VaultImportError

EXPORT_FIELDS = ["title", "username", "password", "url", "notes"]

# Map lowercased source headers onto our field names.
_ALIASES = {
    "title": "title",
    "name": "title",
    "account": "title",
    "username": "username",
    "user": "username",
    "login": "username",
    "login_username": "username",
    "email": "username",
    "password": "password",
    "pass": "password",
    "login_password": "password",
    "url": "url",
    "website": "url",
    "uri": "url",
    "login_uri": "url",
    "notes": "notes",
    "note": "notes",
    "comment": "notes",
}


def export_csv(entries: list[Entry], path: str | os.PathLike[str]) -> None:
    """Write entries to a CSV file (plaintext — handle with care)."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=EXPORT_FIELDS)
        writer.writeheader()
        for e in entries:
            writer.writerow(
                {
                    "title": e.title,
                    "username": e.username,
                    "password": e.password,
                    "url": e.url,
                    "notes": e.notes,
                }
            )


def import_csv(path: str | os.PathLike[str]) -> list[Entry]:
    """Parse a CSV export into entries, tolerating varied column headers.

    A row needs at least a title (or a name/url to fall back on) to be imported.
    """
    text = Path(path).read_text(encoding="utf-8-sig")  # tolerate BOM
    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames is None:
        raise VaultImportError("CSV file has no header row")

    mapping = {
        col: _ALIASES[col.strip().lower()]
        for col in reader.fieldnames
        if col and col.strip().lower() in _ALIASES
    }
    if "title" not in mapping.values() and "url" not in mapping.values():
        raise VaultImportError("could not find a title/name or url column to import from")

    entries: list[Entry] = []
    for row in reader:
        fields = {"title": "", "username": "", "password": "", "url": "", "notes": ""}
        for col, target in mapping.items():
            value = (row.get(col) or "").strip()
            if value and not fields[target]:
                fields[target] = value
        # Skip completely empty rows before applying any title fallback.
        if not any(fields.values()):
            continue
        if not fields["title"]:
            fields["title"] = fields["url"] or "(untitled)"
        entries.append(Entry(**fields))
    return entries
