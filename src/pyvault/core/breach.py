"""Check passwords against Have I Been Pwned using k-anonymity.

Privacy model: the password never leaves this machine. We compute its SHA-1
locally and send only the **first 5 hex characters** of that hash to the API.
The service returns every breached-hash *suffix* sharing that prefix (hundreds
of them), and we match locally. With the ``Add-Padding`` header the response
size is also randomized, so nothing about the password can be inferred.

SHA-1 is used here solely because that is the index the HIBP dataset uses — it
is not used to protect anything.
"""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from collections.abc import Callable

from pyvault.errors import BreachCheckError

API_ROOT = "https://api.pwnedpasswords.com/range/"
_TIMEOUT = 10

#: A fetcher takes a 5-char hash prefix and returns the raw API response body.
Fetcher = Callable[[str], str]


def _http_fetch(prefix: str) -> str:
    request = urllib.request.Request(  # noqa: S310 (constant https URL)
        f"{API_ROOT}{prefix}",
        headers={"Add-Padding": "true", "User-Agent": "PyVault-PasswordManager"},
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:  # noqa: S310
            return response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise BreachCheckError(f"could not reach the breach-check service: {exc}") from exc


def pwned_count(password: str, *, fetch: Fetcher | None = None) -> int:
    """Return how many known breaches this password appears in (0 if none).

    ``fetch`` is injectable so tests can run without network access.
    """
    if not password:
        return 0
    fetch = fetch or _http_fetch

    digest = (
        hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()
    )  # noqa: S324
    prefix, suffix = digest[:5], digest[5:]

    body = fetch(prefix)
    for line in body.splitlines():
        line_suffix, _, count = line.partition(":")
        if line_suffix.strip() == suffix:
            return int(count.strip() or 0)
    return 0
