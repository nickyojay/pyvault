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
