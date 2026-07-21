"""A lightweight master-password strength estimate.

Deliberately simple (length + character variety) — enough to nudge users away
from weak passwords without pulling in a heavy dependency like zxcvbn.
"""

from __future__ import annotations

import string

WEAK = "Weak"
FAIR = "Fair"
STRONG = "Strong"


def password_strength(password: str) -> str:
    """Return ``"Weak"``, ``"Fair"``, or ``"Strong"``."""
    if not password:
        return WEAK

    classes = 0
    if any(c in string.ascii_lowercase for c in password):
        classes += 1
    if any(c in string.ascii_uppercase for c in password):
        classes += 1
    if any(c in string.digits for c in password):
        classes += 1
    if any(not c.isalnum() for c in password):
        classes += 1

    length = len(password)
    if length >= 16 and classes >= 3:
        return STRONG
    if length >= 12 and classes >= 2:
        return FAIR
    if length >= 8 and classes >= 3:
        return FAIR
    return WEAK
