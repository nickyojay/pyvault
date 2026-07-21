"""Tests for the HIBP k-anonymity breach client (no real network)."""

import hashlib

import pytest

from pyvault.core.breach import pwned_count
from pyvault.errors import BreachCheckError


def _sha1_upper(password: str) -> str:
    return hashlib.sha1(password.encode(), usedforsecurity=False).hexdigest().upper()


def test_detects_breached_password():
    pw = "password123"
    digest = _sha1_upper(pw)
    prefix, suffix = digest[:5], digest[5:]

    captured = {}

    def fake_fetch(sent_prefix):
        captured["prefix"] = sent_prefix
        # API returns suffixes without the shared prefix, "SUFFIX:count".
        return f"{suffix}:4200\nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA:1\n"

    assert pwned_count(pw, fetch=fake_fetch) == 4200
    # Only the 5-char prefix is ever sent.
    assert captured["prefix"] == prefix
    assert len(captured["prefix"]) == 5


def test_clean_password_returns_zero():
    def fake_fetch(_prefix):
        return "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:9\n"

    assert pwned_count("some-unbreached-value", fetch=fake_fetch) == 0


def test_empty_password_skips_network():
    def fail_fetch(_prefix):  # pragma: no cover - must not be called
        raise AssertionError("should not fetch for empty password")

    assert pwned_count("", fetch=fail_fetch) == 0


def test_network_error_wrapped():
    def boom(_prefix):
        raise BreachCheckError("offline")

    with pytest.raises(BreachCheckError):
        pwned_count("whatever", fetch=boom)
