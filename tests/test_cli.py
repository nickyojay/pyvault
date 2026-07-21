"""Tests for the CLI harness.

The master-password prompts and the (slow) KDF are patched so the whole vault
lifecycle can be driven quickly and non-interactively.
"""

import pytest

from pyvault import cli
from pyvault.crypto.kdf import KdfParams

PASSWORD = "correct-horse-9"


@pytest.fixture
def vault_env(tmp_path, monkeypatch):
    """A CLI wired to a temp vault, mocked prompts, and fast Argon2id."""
    path = tmp_path / "vault.vault"
    monkeypatch.setattr(cli, "_read_password", lambda *a, **k: PASSWORD)
    monkeypatch.setattr(cli, "_read_new_password", lambda: PASSWORD)
    monkeypatch.setattr(
        cli, "_new_kdf_params", lambda: KdfParams.create(time_cost=1, memory_cost=64, parallelism=1)
    )

    def run(*args):
        return cli.main(["--vault", str(path), *args])

    return run, path


def test_gen_outputs_password(capsys):
    assert cli.main(["gen", "--length", "24"]) == 0
    out = capsys.readouterr().out.strip()
    assert len(out) == 24


def test_gen_no_symbols(capsys):
    cli.main(["gen", "--length", "30", "--no-symbols"])
    out = capsys.readouterr().out.strip()
    assert out.isalnum()


def test_init_creates_vault(vault_env, capsys):
    run, path = vault_env
    assert run("init") == 0
    assert path.exists()
    assert "Created new vault" in capsys.readouterr().out


def test_init_refuses_existing_without_force(vault_env):
    run, _ = vault_env
    run("init")
    assert run("init") == 1  # already exists


def test_add_get_roundtrip(vault_env, capsys):
    run, _ = vault_env
    run("init")
    capsys.readouterr()
    assert run("add", "GitHub", "-u", "nick", "-p", "hunter2", "--url", "https://gh.com") == 0
    capsys.readouterr()

    assert run("get", "GitHub", "--show") == 0
    out = capsys.readouterr().out
    assert "nick" in out
    assert "hunter2" in out


def test_get_masks_password_by_default(vault_env, capsys):
    run, _ = vault_env
    run("init")
    run("add", "GitHub", "-p", "hunter2")
    capsys.readouterr()
    run("get", "GitHub")
    out = capsys.readouterr().out
    assert "hunter2" not in out
    assert "********" in out


def test_add_generate_creates_strong_password(vault_env, capsys):
    run, _ = vault_env
    run("init")
    capsys.readouterr()
    run("add", "Email", "-g", "-l", "18")
    out = capsys.readouterr().out
    assert "Generated password:" in out
    generated = out.split("Generated password:")[1].strip()
    assert len(generated) == 18


def test_list_and_rm(vault_env, capsys):
    run, _ = vault_env
    run("init")
    run("add", "GitHub", "-p", "x")
    run("add", "Email", "-p", "y")
    capsys.readouterr()

    run("list")
    out = capsys.readouterr().out
    assert "GitHub" in out and "Email" in out

    assert run("rm", "GitHub") == 0
    capsys.readouterr()
    run("list")
    out = capsys.readouterr().out
    assert "GitHub" not in out
    assert "Email" in out


def test_get_missing_entry_errors(vault_env):
    run, _ = vault_env
    run("init")
    assert run("get", "Nonexistent") == 1


def test_commands_fail_without_vault(vault_env):
    run, _ = vault_env
    assert run("list") == 1  # no vault created yet
