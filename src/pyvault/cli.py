"""Command-line harness for PyVault.

This is a temporary, pragmatic front-end (Phase 2) that exercises the crypto and
core layers end-to-end before the GUI arrives in Phase 3. It is fully usable on
its own.

Vault location resolves in this order: ``--vault PATH`` > ``$PYVAULT_VAULT`` >
``~/.pyvault/vault.vault``.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

from pyvault import __version__
from pyvault.core.controller import VaultController
from pyvault.core.generator import generate_password
from pyvault.core.model import Entry
from pyvault.core.vault_file import (
    LoadedVault,
    create_vault,
    open_vault,
    save_vault,
)
from pyvault.crypto.kdf import KdfParams
from pyvault.errors import VaultError

DEFAULT_VAULT = Path.home() / ".pyvault" / "vault.vault"
MIN_PASSWORD_LEN = 8


# --- password prompts (indirected so tests can monkeypatch) ------------


def _read_password(prompt: str = "Master password: ") -> str:
    return getpass.getpass(prompt)


def _read_new_password() -> str:
    while True:
        first = getpass.getpass("New master password: ")
        if len(first) < MIN_PASSWORD_LEN:
            print(f"Password must be at least {MIN_PASSWORD_LEN} characters.", file=sys.stderr)
            continue
        if first != getpass.getpass("Confirm master password: "):
            print("Passwords did not match, try again.", file=sys.stderr)
            continue
        return first


def _new_kdf_params() -> KdfParams | None:
    """KDF params for a new vault. ``None`` means use the library defaults.

    Overridden in tests to keep Argon2id fast.
    """
    return None


# --- helpers -----------------------------------------------------------


def _resolve_path(args: argparse.Namespace) -> Path:
    return Path(args.vault or os.environ.get("PYVAULT_VAULT") or DEFAULT_VAULT)


def _open(args: argparse.Namespace) -> LoadedVault:
    path = _resolve_path(args)
    if not path.exists():
        raise VaultError(f"no vault at {path} (run `pyvault init` first)")
    return open_vault(path, _read_password())


def _find(loaded: LoadedVault, needle: str) -> Entry:
    """Locate an entry by exact id, then by exact or substring title match."""
    entry = loaded.vault.get(needle)
    if entry is not None:
        return entry
    matches = [e for e in loaded.vault.entries if needle.lower() in e.title.lower()]
    if not matches:
        raise VaultError(f"no entry matching {needle!r}")
    if len(matches) > 1:
        titles = ", ".join(f"{e.title} ({e.id[:8]})" for e in matches)
        raise VaultError(f"{needle!r} is ambiguous; matches: {titles}")
    return matches[0]


# --- commands ----------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    path = _resolve_path(args)
    if path.exists() and not args.force:
        print(f"Vault already exists at {path} (use --force to overwrite).", file=sys.stderr)
        return 1
    password = _read_new_password()
    print("Deriving key (Argon2id is intentionally slow)...", file=sys.stderr)
    create_vault(path, password, kdf_params=_new_kdf_params())
    print(f"Created new vault at {path}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    loaded = _open(args)
    if args.generate:
        password = generate_password(args.length)
    elif args.password is not None:
        password = args.password
    else:
        password = getpass.getpass("Entry password (blank to leave empty): ")
    entry = loaded.vault.add(
        Entry(
            title=args.title,
            username=args.username or "",
            password=password,
            url=args.url or "",
            notes=args.notes or "",
        )
    )
    save_vault(_resolve_path(args), loaded)
    print(f"Added {entry.title!r} ({entry.id[:8]})")
    if args.generate:
        print(f"Generated password: {password}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    loaded = _open(args)
    entries = loaded.vault.search(args.query or "")
    if not entries:
        print("(no entries)")
        return 0
    width = max(len(e.title) for e in entries)
    for e in sorted(entries, key=lambda e: e.title.lower()):
        print(f"{e.id[:8]}  {e.title:<{width}}  {e.username}")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    loaded = _open(args)
    entry = _find(loaded, args.name)
    print(f"Title:    {entry.title}")
    print(f"Username: {entry.username}")
    print(f"URL:      {entry.url}")
    print(f"Password: {entry.password if args.show else '********'}")
    if entry.notes:
        print(f"Notes:    {entry.notes}")
    if not args.show:
        print("(use --show to reveal the password)", file=sys.stderr)
    return 0


def cmd_rm(args: argparse.Namespace) -> int:
    loaded = _open(args)
    entry = _find(loaded, args.name)
    loaded.vault.delete(entry.id)
    save_vault(_resolve_path(args), loaded)
    print(f"Removed {entry.title!r} ({entry.id[:8]})")
    return 0


def cmd_passwd(args: argparse.Namespace) -> int:
    path = _resolve_path(args)
    if not path.exists():
        raise VaultError(f"no vault at {path}")
    controller = VaultController(path)
    current = _read_password("Current master password: ")
    controller.unlock(current)
    new = _read_new_password()
    print("Deriving key (Argon2id is intentionally slow)...", file=sys.stderr)
    controller.change_password(current, new)
    print("Master password changed.")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    path = _resolve_path(args)
    if not path.exists():
        raise VaultError(f"no vault at {path}")
    controller = VaultController(path)
    controller.unlock(_read_password())
    controller.export_csv(args.file)
    print(f"Exported to {args.file}")
    print("WARNING: this CSV contains plaintext passwords. Delete it when done.", file=sys.stderr)
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    path = _resolve_path(args)
    if not path.exists():
        raise VaultError(f"no vault at {path} (run `pyvault init` first)")
    controller = VaultController(path)
    controller.unlock(_read_password())
    count = controller.import_csv(args.file)
    print(f"Imported {count} entr{'y' if count == 1 else 'ies'} from {args.file}")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    path = _resolve_path(args)
    if not path.exists():
        raise VaultError(f"no vault at {path}")
    controller = VaultController(path)
    controller.unlock(_read_password())
    rows = controller.audit()

    breaches: dict[str, int] = {}
    if args.online:
        print(
            "Checking Have I Been Pwned (only a 5-char hash prefix is sent)...",
            file=sys.stderr,
        )
        breaches = controller.check_all_breaches()

    issues = 0
    for row in rows:
        flags = []
        if row.weak:
            flags.append("WEAK")
        if row.reused:
            flags.append("REUSED")
        count = breaches.get(row.entry.id, 0)
        if count:
            flags.append(f"BREACHED x{count}")
        if flags:
            issues += 1
            print(f"{row.entry.title}: {', '.join(flags)}")

    scope = "issues" if args.online else "offline issues"
    print(f"\n{issues} {scope} found." if issues else f"No {scope} found.")
    return 0


def cmd_gen(args: argparse.Namespace) -> int:
    print(
        generate_password(
            args.length,
            symbols=not args.no_symbols,
            avoid_ambiguous=args.no_ambiguous,
        )
    )
    return 0


# --- parser ------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyvault", description="PyVault password manager (CLI)")
    parser.add_argument("--version", action="version", version=f"pyvault {__version__}")
    parser.add_argument("--vault", help="path to the vault file (overrides $PYVAULT_VAULT)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create a new empty vault")
    p_init.add_argument("--force", action="store_true", help="overwrite an existing vault")
    p_init.set_defaults(func=cmd_init)

    p_add = sub.add_parser("add", help="add an entry")
    p_add.add_argument("title")
    p_add.add_argument("-u", "--username")
    p_add.add_argument("--url")
    p_add.add_argument("--notes")
    p_add.add_argument("-p", "--password", help="set password inline (else prompted)")
    p_add.add_argument("-g", "--generate", action="store_true", help="generate a password")
    p_add.add_argument("-l", "--length", type=int, default=20, help="generated password length")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="list entries")
    p_list.add_argument("query", nargs="?", help="filter by title/username/url")
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get", help="show a single entry")
    p_get.add_argument("name", help="entry id (or unique title substring)")
    p_get.add_argument("-s", "--show", action="store_true", help="reveal the password")
    p_get.set_defaults(func=cmd_get)

    p_rm = sub.add_parser("rm", help="delete an entry")
    p_rm.add_argument("name", help="entry id (or unique title substring)")
    p_rm.set_defaults(func=cmd_rm)

    p_passwd = sub.add_parser("passwd", help="change the master password")
    p_passwd.set_defaults(func=cmd_passwd)

    p_audit = sub.add_parser("audit", help="find weak/reused (and optionally breached) passwords")
    p_audit.add_argument(
        "--online",
        action="store_true",
        help="also check Have I Been Pwned (sends only hash prefixes)",
    )
    p_audit.set_defaults(func=cmd_audit)

    p_export = sub.add_parser("export", help="export entries to a CSV file (plaintext!)")
    p_export.add_argument("file", help="destination .csv path")
    p_export.set_defaults(func=cmd_export)

    p_import = sub.add_parser("import", help="import entries from a CSV file")
    p_import.add_argument("file", help="source .csv path")
    p_import.set_defaults(func=cmd_import)

    p_gen = sub.add_parser("gen", help="generate a password (no vault needed)")
    p_gen.add_argument("-l", "--length", type=int, default=20)
    p_gen.add_argument("--no-symbols", action="store_true")
    p_gen.add_argument("--no-ambiguous", action="store_true", help="exclude look-alike chars")
    p_gen.set_defaults(func=cmd_gen)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except VaultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\naborted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
