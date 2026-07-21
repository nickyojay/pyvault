"""Tests for AES-256-GCM authenticated encryption."""

import pytest

from pyvault.crypto.cipher import NONCE_LEN, decrypt, encrypt
from pyvault.errors import InvalidPasswordError

KEY = b"0" * 32
OTHER_KEY = b"1" * 32


def test_roundtrip():
    nonce, ct = encrypt(KEY, b"secret message")
    assert len(nonce) == NONCE_LEN
    assert decrypt(KEY, nonce, ct) == b"secret message"


def test_nonce_is_unique_per_encryption():
    n1, _ = encrypt(KEY, b"x")
    n2, _ = encrypt(KEY, b"x")
    assert n1 != n2


def test_wrong_key_fails():
    nonce, ct = encrypt(KEY, b"secret")
    with pytest.raises(InvalidPasswordError):
        decrypt(OTHER_KEY, nonce, ct)


def test_tampered_ciphertext_fails():
    nonce, ct = encrypt(KEY, b"secret")
    tampered = bytearray(ct)
    tampered[0] ^= 0x01
    with pytest.raises(InvalidPasswordError):
        decrypt(KEY, nonce, bytes(tampered))


def test_aad_must_match():
    nonce, ct = encrypt(KEY, b"secret", aad=b"header-v1")
    assert decrypt(KEY, nonce, ct, aad=b"header-v1") == b"secret"
    with pytest.raises(InvalidPasswordError):
        decrypt(KEY, nonce, ct, aad=b"header-v2")
