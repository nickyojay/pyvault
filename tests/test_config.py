"""Tests for application settings persistence."""

from pyvault.core.config import Config


def test_defaults():
    cfg = Config()
    assert cfg.auto_lock_minutes == 5
    assert cfg.clipboard_clear_seconds == 15
    assert cfg.vault_path.endswith("vault.vault")


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    cfg = Config(
        vault_path=str(tmp_path / "my.vault"), auto_lock_minutes=2, clipboard_clear_seconds=30
    )
    cfg.save(path)
    loaded = Config.load(path)
    assert loaded == cfg


def test_load_missing_returns_defaults(tmp_path):
    assert Config.load(tmp_path / "nope.json") == Config()


def test_load_ignores_unknown_keys(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"vault_path": "/x.vault", "bogus": 1}')
    cfg = Config.load(path)
    assert cfg.vault_path == "/x.vault"


def test_load_corrupt_returns_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("not json {")
    assert Config.load(path) == Config()
