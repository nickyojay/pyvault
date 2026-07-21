"""Tests for Argon2id key derivation."""

from pyvault.crypto.kdf import KEY_LEN, SALT_LEN, KdfParams, derive_key


def test_create_generates_random_salt():
    a = KdfParams.create()
    b = KdfParams.create()
    assert len(a.salt) == SALT_LEN
    assert a.salt != b.salt


def test_derive_key_is_deterministic(fast_kdf_params):
    k1 = derive_key("correct horse battery staple", fast_kdf_params)
    k2 = derive_key("correct horse battery staple", fast_kdf_params)
    assert k1 == k2
    assert len(k1) == KEY_LEN


def test_different_password_gives_different_key(fast_kdf_params):
    k1 = derive_key("password-one", fast_kdf_params)
    k2 = derive_key("password-two", fast_kdf_params)
    assert k1 != k2


def test_different_salt_gives_different_key():
    p1 = KdfParams.create(time_cost=1, memory_cost=64, parallelism=1)
    p2 = KdfParams.create(time_cost=1, memory_cost=64, parallelism=1)
    assert derive_key("same-password", p1) != derive_key("same-password", p2)


def test_params_roundtrip_through_dict(fast_kdf_params):
    restored = KdfParams.from_dict(fast_kdf_params.to_dict())
    assert restored == fast_kdf_params
