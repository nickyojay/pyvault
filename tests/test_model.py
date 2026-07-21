"""Tests for the in-memory vault model and its serialization."""

import pytest

from pyvault.core.model import Entry, Vault
from pyvault.errors import VaultCorruptError


def test_add_and_get():
    vault = Vault()
    entry = vault.add(Entry(title="GitHub", username="nick", password="hunter2"))
    assert vault.get(entry.id) is entry
    assert len(vault.entries) == 1


def test_update_changes_fields_and_timestamp():
    vault = Vault()
    entry = vault.add(Entry(title="GitHub"))
    original_updated = entry.updated_at
    vault.update(entry.id, password="new-secret", title="GitHub.com")
    assert entry.password == "new-secret"
    assert entry.title == "GitHub.com"
    assert entry.updated_at >= original_updated


def test_update_rejects_immutable_fields():
    vault = Vault()
    entry = vault.add(Entry(title="X"))
    with pytest.raises(AttributeError):
        vault.update(entry.id, id="hacked")


def test_update_unknown_id_raises():
    vault = Vault()
    with pytest.raises(KeyError):
        vault.update("nope", title="x")


def test_delete():
    vault = Vault()
    entry = vault.add(Entry(title="X"))
    vault.delete(entry.id)
    assert vault.get(entry.id) is None
    with pytest.raises(KeyError):
        vault.delete(entry.id)


def test_search_matches_title_username_url():
    vault = Vault()
    vault.add(Entry(title="GitHub", username="nick", url="https://github.com"))
    vault.add(Entry(title="Email", username="bob", url="https://mail.com"))
    assert len(vault.search("git")) == 1
    assert len(vault.search("BOB")) == 1
    assert len(vault.search("")) == 2


def test_vault_roundtrip_through_dict():
    vault = Vault()
    vault.add(Entry(title="A", username="u", password="p", tags=["work"]))
    vault.add(Entry(title="B", notes="hello"))
    restored = Vault.from_dict(vault.to_dict())
    assert [e.to_dict() for e in restored.entries] == [e.to_dict() for e in vault.entries]


def test_from_dict_rejects_bad_version():
    data = Vault().to_dict()
    data["version"] = 999
    with pytest.raises(VaultCorruptError):
        Vault.from_dict(data)


def test_entry_from_dict_rejects_missing_fields():
    with pytest.raises(VaultCorruptError):
        Entry.from_dict({"title": "no id or timestamps"})
