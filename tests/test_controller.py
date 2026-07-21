"""Tests for the GUI-agnostic VaultController (no Qt)."""

import pytest

from pyvault.core.controller import VaultController
from pyvault.crypto.kdf import KdfParams
from pyvault.errors import InvalidPasswordError, VaultError

PASSWORD = "master-pass-123"
FAST = dict(time_cost=1, memory_cost=64, parallelism=1)


@pytest.fixture
def controller(tmp_path):
    return VaultController(tmp_path / "vault.vault", kdf_params=KdfParams.create(**FAST))


def test_starts_locked_and_absent(controller):
    assert not controller.is_unlocked
    assert not controller.vault_exists()


def test_create_unlocks_and_persists(controller):
    controller.create(PASSWORD)
    assert controller.is_unlocked
    assert controller.vault_exists()


def test_create_refuses_existing(controller):
    controller.create(PASSWORD)
    controller.lock()
    with pytest.raises(VaultError):
        controller.create(PASSWORD)


def test_lock_then_unlock(controller):
    controller.create(PASSWORD)
    controller.add_entry(title="GitHub", password="x")
    controller.lock()
    assert not controller.is_unlocked
    controller.unlock(PASSWORD)
    assert len(controller.entries()) == 1


def test_unlock_wrong_password(controller):
    controller.create(PASSWORD)
    controller.lock()
    with pytest.raises(InvalidPasswordError):
        controller.unlock("wrong")


def test_add_update_delete_autosave(controller, tmp_path):
    controller.create(PASSWORD)
    entry = controller.add_entry(title="GitHub", username="nick", password="p1")
    controller.update_entry(entry.id, password="p2")
    # A fresh controller reading the same file must see the persisted change.
    fresh = VaultController(tmp_path / "vault.vault")
    fresh.unlock(PASSWORD)
    assert fresh.get(entry.id).password == "p2"

    controller.delete_entry(entry.id)
    fresh2 = VaultController(tmp_path / "vault.vault")
    fresh2.unlock(PASSWORD)
    assert fresh2.get(entry.id) is None


def test_operations_require_unlock(controller):
    with pytest.raises(VaultError):
        controller.entries()
    with pytest.raises(VaultError):
        controller.add_entry(title="x")


def test_search(controller):
    controller.create(PASSWORD)
    controller.add_entry(title="GitHub", username="nick")
    controller.add_entry(title="Email", username="bob")
    assert len(controller.search("git")) == 1
    assert len(controller.search("")) == 2


def test_set_path_locks(controller, tmp_path):
    controller.create(PASSWORD)
    controller.set_path(tmp_path / "other.vault")
    assert not controller.is_unlocked
    assert controller.path.name == "other.vault"


# --- change master password -------------------------------------------
def test_change_password(controller, tmp_path):
    controller.create(PASSWORD)
    entry = controller.add_entry(title="GitHub", password="x")
    controller.change_password(PASSWORD, "brand-new-pass-9")
    controller.lock()

    with pytest.raises(InvalidPasswordError):
        controller.unlock(PASSWORD)  # old password no longer works
    controller.unlock("brand-new-pass-9")
    assert controller.get(entry.id).password == "x"


def test_change_password_wrong_current(controller):
    controller.create(PASSWORD)
    with pytest.raises(InvalidPasswordError):
        controller.change_password("not-the-current", "brand-new-pass-9")


def test_change_password_uses_fresh_salt(controller):
    controller.create(PASSWORD)
    before = controller._loaded.kdf_params.salt
    controller.change_password(PASSWORD, "brand-new-pass-9")
    assert controller._loaded.kdf_params.salt != before


# --- CSV import / export ----------------------------------------------
def test_export_and_import_csv(controller, tmp_path):
    controller.create(PASSWORD)
    controller.add_entry(title="GitHub", username="nick", password="p1")
    csv_path = tmp_path / "dump.csv"
    controller.export_csv(csv_path)

    other = VaultController(tmp_path / "other.vault", kdf_params=KdfParams.create(**FAST))
    other.create("another-pass-1")
    added = other.import_csv(csv_path)
    assert added == 1
    assert other.entries()[0].title == "GitHub"


# --- sync-conflict preservation ---------------------------------------
def test_external_change_preserved_on_save(controller, tmp_path):
    controller.create(PASSWORD)
    controller.add_entry(title="First", password="x")

    # Simulate another device syncing a different copy over our file.
    import os
    import time

    other_bytes = (tmp_path / "vault.vault").read_bytes()
    time.sleep(0.01)
    (tmp_path / "vault.vault").write_bytes(other_bytes + b"\n")
    # Force a distinct mtime in case the clock is coarse.
    future = time.time() + 5
    os.utime(tmp_path / "vault.vault", (future, future))

    controller.add_entry(title="Second", password="y")  # triggers a save
    assert controller.last_conflict_path is not None
    assert controller.last_conflict_path.exists()
    # Our change still persisted.
    assert len(controller.entries()) == 2


def test_no_conflict_on_normal_saves(controller):
    controller.create(PASSWORD)
    controller.add_entry(title="First", password="x")
    controller.add_entry(title="Second", password="y")
    assert controller.last_conflict_path is None
