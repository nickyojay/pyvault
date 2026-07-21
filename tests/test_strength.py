"""Tests for the password strength estimate."""

import pytest

from pyvault.core.strength import FAIR, STRONG, WEAK, password_strength


@pytest.mark.parametrize(
    "password, expected",
    [
        ("", WEAK),
        ("short", WEAK),
        ("password", WEAK),  # 8 chars, one class
        ("password1234", FAIR),  # 12 chars, two classes
        ("Abcd1234", FAIR),  # 8 chars, three classes
        ("Xy7!Xy7!Xy7!Xy7!", STRONG),  # 16 chars, four classes
        ("correcthorsebatterystaple9X", STRONG),  # long + mixed
    ],
)
def test_strength_levels(password, expected):
    assert password_strength(password) == expected
