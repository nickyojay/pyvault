"""Cryptographically secure password generation.

Uses :mod:`secrets` (the OS CSPRNG) throughout — never :mod:`random`. Shared by
the CLI and the future GUI.
"""

from __future__ import annotations

import secrets
import string

LOWER = string.ascii_lowercase
UPPER = string.ascii_uppercase
DIGITS = string.digits
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.?/"

# Characters that are easy to confuse in many fonts.
AMBIGUOUS = set("Il1O0oB8S5Z2")


def generate_password(
    length: int = 20,
    *,
    lower: bool = True,
    upper: bool = True,
    digits: bool = True,
    symbols: bool = True,
    avoid_ambiguous: bool = False,
) -> str:
    """Generate a random password.

    Guarantees at least one character from each enabled class. Raises
    ``ValueError`` if no class is enabled or ``length`` is too small to include
    one character from every enabled class.
    """
    pools: list[str] = []
    for enabled, chars in (
        (lower, LOWER),
        (upper, UPPER),
        (digits, DIGITS),
        (symbols, SYMBOLS),
    ):
        if not enabled:
            continue
        if avoid_ambiguous:
            chars = "".join(c for c in chars if c not in AMBIGUOUS)
        if chars:
            pools.append(chars)

    if not pools:
        raise ValueError("at least one character class must be enabled")
    if length < len(pools):
        raise ValueError(
            f"length {length} is too short to include all {len(pools)} character classes"
        )

    alphabet = "".join(pools)
    # One guaranteed character per enabled class, then fill the remainder.
    chars = [secrets.choice(pool) for pool in pools]
    chars += [secrets.choice(alphabet) for _ in range(length - len(pools))]

    # Fisher-Yates shuffle using the CSPRNG so guaranteed chars aren't front-loaded.
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]

    return "".join(chars)
