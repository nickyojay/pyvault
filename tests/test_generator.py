"""Tests for CSPRNG password generation."""

import string

import pytest

from pyvault.core.generator import AMBIGUOUS, SYMBOLS, generate_password


def test_default_length():
    assert len(generate_password()) == 20


def test_custom_length():
    assert len(generate_password(32)) == 32


def test_includes_one_of_each_enabled_class():
    pw = generate_password(40)
    assert any(c in string.ascii_lowercase for c in pw)
    assert any(c in string.ascii_uppercase for c in pw)
    assert any(c in string.digits for c in pw)
    assert any(c in SYMBOLS for c in pw)


def test_no_symbols_excludes_symbols():
    pw = generate_password(40, symbols=False)
    assert not any(c in SYMBOLS for c in pw)


def test_avoid_ambiguous():
    pw = generate_password(60, avoid_ambiguous=True)
    assert not any(c in AMBIGUOUS for c in pw)


def test_no_class_enabled_raises():
    with pytest.raises(ValueError):
        generate_password(lower=False, upper=False, digits=False, symbols=False)


def test_length_too_short_for_classes_raises():
    with pytest.raises(ValueError):
        generate_password(2)  # 4 classes enabled, need >= 4


def test_passwords_are_unique():
    assert len({generate_password() for _ in range(50)}) == 50
