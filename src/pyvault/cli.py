"""Temporary command-line harness (fleshed out in Phase 2).

This exists to exercise the crypto/core layers end-to-end before the GUI lands.
"""

import argparse

from pyvault import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyvault", description="PyVault password manager (CLI)")
    parser.add_argument("--version", action="version", version=f"pyvault {__version__}")
    return parser


def main() -> int:
    parser = build_parser()
    parser.parse_args()
    print(f"PyVault {__version__} — CLI harness coming in Phase 2.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
