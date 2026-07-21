"""Tests for the encrypted vault file format and safe I/O."""

import json

import pytest

from pyvault.core.model import Entry
from pyvault.core.vault_file import (
    create_vault,
    open_vault,
    save_vault,
)
from pyvault.errors import (
    InvalidPasswordError,
    VaultCorruptError,
    VaultVersionError,
)

PASSWORD = "master-pass-123"
FAST_KDF = dict(time_cost=1, memory_cost=64, parallelism=1)


def _make_vault(path):
    from pyvault.crypto.kdf import KdfParams

    return create_vault(path, PASSWORD, kdf_params=KdfParams.create(**FAST_KDF))


def test_create_and_reopen_roundtrip(tmp_path):
    path = tmp_path / "vault.vault"
    loaded = _make_vault(path)
    loaded.vault.add(Entry(title="GitHub", username="nick", password="hunter2"))
    save_vault(path, loaded)

    reopened = open_vault(path, PASSWORD)
    assert len(reopened.vault.entries) == 1
    entry = reopened.vault.entries[0]
    assert entry.title == "GitHub"
    assert entry.password == "hunter2"


def test_file_contains_no_plaintext_secret(tmp_path):
    path = tmp_path / "vault.vault"
    loaded = _make_vault(path)
    loaded.vault.add(Entry(title="GitHub", password="super-secret-value"))
    save_vault(path, loaded)
    raw = path.read_bytes()
    assert b"super-secret-value" not in raw
    assert b"GitHub" not in raw


def test_wrong_password_rejected(tmp_path):
    path = tmp_path / "vault.vault"
    _make_vault(path)
    with pytest.raises(InvalidPasswordError):
        open_vault(path, "wrong-password")


def test_tampered_ciphertext_rejected(tmp_path):
    path = tmp_path / "vault.vault"
    _make_vault(path)
    envelope = json.loads(path.read_text())
    # Flip a character in the base64 ciphertext.
    ct = envelope["ciphertext"]
    envelope["ciphertext"] = ("A" if ct[0] != "A" else "B") + ct[1:]
    path.write_text(json.dumps(envelope))
    with pytest.raises((InvalidPasswordError, VaultCorruptError)):
        open_vault(path, PASSWORD)


def test_tampered_kdf_header_rejected(tmp_path):
    # Changing the salt (bound as AAD) must break authentication.
    path = tmp_path / "vault.vault"
    _make_vault(path)
    envelope = json.loads(path.read_text())
    salt = envelope["kdf"]["salt"]
    envelope["kdf"]["salt"] = ("A" if salt[0] != "A" else "B") + salt[1:]
    path.write_text(json.dumps(envelope))
    with pytest.raises(InvalidPasswordError):
        open_vault(path, PASSWORD)


def test_corrupt_json_rejected(tmp_path):
    path = tmp_path / "vault.vault"
    path.write_text("this is not json {")
    with pytest.raises(VaultCorruptError):
        open_vault(path, PASSWORD)


def test_bad_magic_rejected(tmp_path):
    path = tmp_path / "vault.vault"
    path.write_text(json.dumps({"magic": "NOPE", "format": 1}))
    with pytest.raises(VaultCorruptError):
        open_vault(path, PASSWORD)


def test_unknown_format_version_rejected(tmp_path):
    path = tmp_path / "vault.vault"
    _make_vault(path)
    envelope = json.loads(path.read_text())
    envelope["format"] = 999
    path.write_text(json.dumps(envelope))
    with pytest.raises(VaultVersionError):
        open_vault(path, PASSWORD)


def test_save_creates_backup_of_previous(tmp_path):
    path = tmp_path / "vault.vault"
    loaded = _make_vault(path)  # first write, no backup yet
    bak = tmp_path / "vault.vault.bak"
    assert not bak.exists()

    loaded.vault.add(Entry(title="second write"))
    save_vault(path, loaded)  # second write should back up the first
    assert bak.exists()
    # The backup must be the *previous* (empty) vault, still openable.
    assert len(open_vault(bak, PASSWORD).vault.entries) == 0
    assert len(open_vault(path, PASSWORD).vault.entries) == 1


def test_no_tmp_file_left_behind(tmp_path):
    path = tmp_path / "vault.vault"
    _make_vault(path)
    assert not (tmp_path / "vault.vault.tmp").exists()
