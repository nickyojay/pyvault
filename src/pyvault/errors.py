"""Shared exception types for PyVault."""


class VaultError(Exception):
    """Base class for all PyVault errors."""


class InvalidPasswordError(VaultError):
    """The master password was wrong, or the vault has been tampered with.

    Authenticated encryption cannot distinguish a wrong key from a modified
    ciphertext, so both surface as this error.
    """


class VaultCorruptError(VaultError):
    """The vault file is malformed, truncated, or otherwise unreadable."""


class VaultVersionError(VaultError):
    """The vault file uses a format version this build does not understand."""


class VaultImportError(VaultError):
    """An import file could not be parsed."""
