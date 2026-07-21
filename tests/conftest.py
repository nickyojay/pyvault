"""Shared test fixtures."""

import pytest

from pyvault.crypto.kdf import KdfParams

# Deliberately weak Argon2id params so the test suite runs fast. Production code
# uses the much heavier defaults in pyvault.crypto.kdf.
FAST_KDF = dict(time_cost=1, memory_cost=64, parallelism=1)


@pytest.fixture
def fast_kdf_params() -> KdfParams:
    return KdfParams.create(**FAST_KDF)
