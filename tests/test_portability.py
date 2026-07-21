"""Tests for CSV import/export."""

import pytest

from pyvault.core.model import Entry
from pyvault.core.portability import export_csv, import_csv
from pyvault.errors import VaultImportError


def test_export_then_import_roundtrip(tmp_path):
    path = tmp_path / "out.csv"
    entries = [
        Entry(title="GitHub", username="nick", password="p1", url="https://gh.com", notes="n"),
        Entry(title="Email", username="bob", password="p2"),
    ]
    export_csv(entries, path)
    imported = import_csv(path)
    assert [(e.title, e.username, e.password) for e in imported] == [
        ("GitHub", "nick", "p1"),
        ("Email", "bob", "p2"),
    ]


def test_import_chrome_style_headers(tmp_path):
    path = tmp_path / "chrome.csv"
    path.write_text("name,url,username,password,note\nGitHub,https://gh.com,nick,secret,hi\n")
    entries = import_csv(path)
    assert len(entries) == 1
    assert entries[0].title == "GitHub"
    assert entries[0].url == "https://gh.com"
    assert entries[0].password == "secret"
    assert entries[0].notes == "hi"


def test_import_tolerates_bom_and_login_aliases(tmp_path):
    path = tmp_path / "bom.csv"
    path.write_text("﻿title,login,pass\nSite,alice,pw\n")
    entries = import_csv(path)
    assert entries[0].username == "alice"
    assert entries[0].password == "pw"


def test_import_falls_back_to_url_for_title(tmp_path):
    path = tmp_path / "nourl.csv"
    path.write_text("url,username,password\nhttps://x.com,u,p\n")
    entries = import_csv(path)
    assert entries[0].title == "https://x.com"


def test_import_without_usable_columns_raises(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("colour,size\nred,large\n")
    with pytest.raises(VaultImportError):
        import_csv(path)


def test_import_skips_blank_rows(tmp_path):
    path = tmp_path / "blanks.csv"
    path.write_text("title,password\nReal,pw\n,\n")
    assert len(import_csv(path)) == 1
