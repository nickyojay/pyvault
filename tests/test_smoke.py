"""Phase 0 smoke tests: verify the package imports and metadata are wired up."""

import pyvault
from pyvault.cli import build_parser


def test_version_is_exposed():
    assert pyvault.__version__ == "0.1.0"


def test_cli_parser_builds():
    parser = build_parser()
    assert parser.prog == "pyvault"
