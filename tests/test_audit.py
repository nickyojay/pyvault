"""Tests for offline audit (reused / weak detection)."""

from pyvault.core.audit import offline_rows, reused_passwords
from pyvault.core.model import Entry


def _entries():
    return [
        Entry(title="A", password="Xy7!Xy7!Xy7!Xy7!"),  # strong, unique
        Entry(title="B", password="reused-pass-12"),  # reused (with C)
        Entry(title="C", password="reused-pass-12"),  # reused (with B)
        Entry(title="D", password="weak"),  # weak, unique
        Entry(title="E", password=""),  # no password
    ]


def test_reused_passwords():
    assert reused_passwords(_entries()) == {"reused-pass-12"}


def test_offline_rows_flags():
    rows = {row.entry.title: row for row in offline_rows(_entries())}
    assert not rows["A"].weak and not rows["A"].reused
    assert rows["B"].reused and rows["C"].reused
    assert rows["D"].weak and not rows["D"].reused
    assert not rows["E"].weak and not rows["E"].reused  # empty password ignored


def test_pwned_defaults_none():
    rows = offline_rows(_entries())
    assert all(row.pwned is None for row in rows)


def test_has_issue():
    rows = {row.entry.title: row for row in offline_rows(_entries())}
    assert rows["B"].has_issue
    assert rows["D"].has_issue
    assert not rows["A"].has_issue
