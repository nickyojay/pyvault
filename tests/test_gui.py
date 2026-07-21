"""Headless (offscreen) smoke tests for the PySide6 GUI.

These construct real widgets under QT_QPA_PLATFORM=offscreen and drive their
non-visual logic. They intentionally avoid modal ``exec()`` calls.
"""

import pytest

from pyvault.core.config import Config
from pyvault.core.controller import VaultController
from pyvault.crypto.kdf import KdfParams

pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QDialog  # noqa: E402

from pyvault.ui.entry_dialog import EntryDialog  # noqa: E402
from pyvault.ui.generator_dialog import GeneratorDialog  # noqa: E402
from pyvault.ui.main_window import MASK, MainWindow  # noqa: E402
from pyvault.ui.unlock import CreateVaultDialog, UnlockDialog  # noqa: E402

PASSWORD = "master-pass-123"
FAST = dict(time_cost=1, memory_cost=64, parallelism=1)


@pytest.fixture(autouse=True)
def _no_modal_dialogs(monkeypatch):
    """Neutralize modal QMessageBox popups so headless tests never block."""
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))


@pytest.fixture
def unlocked(tmp_path):
    """A controller with an unlocked vault holding two entries, plus a config."""
    controller = VaultController(tmp_path / "vault.vault", kdf_params=KdfParams.create(**FAST))
    controller.create(PASSWORD)
    controller.add_entry(title="GitHub", username="nick", password="hunter2")
    controller.add_entry(title="Email", username="bob", password="s3cret")
    config = Config(vault_path=str(tmp_path / "vault.vault"))
    return controller, config


# --- generator dialog --------------------------------------------------
def test_generator_produces_password(qtbot):
    dlg = GeneratorDialog(length=24)
    qtbot.addWidget(dlg)
    assert len(dlg.password()) == 24


def test_generator_length_updates(qtbot):
    dlg = GeneratorDialog(length=16)
    qtbot.addWidget(dlg)
    dlg._length.setValue(40)
    assert len(dlg.password()) == 40


# --- entry dialog ------------------------------------------------------
def test_entry_dialog_prefills_and_returns_values(qtbot):
    from pyvault.core.model import Entry

    entry = Entry(title="GitHub", username="nick", password="hunter2", url="https://gh.com")
    dlg = EntryDialog(entry=entry)
    qtbot.addWidget(dlg)
    vals = dlg.values()
    assert vals["title"] == "GitHub"
    assert vals["password"] == "hunter2"


def test_entry_dialog_requires_title(qtbot):
    dlg = EntryDialog()
    qtbot.addWidget(dlg)
    dlg._title.setText("   ")
    dlg._on_accept()
    assert dlg.result() != QDialog.Accepted


# --- unlock / create dialogs ------------------------------------------
def test_create_dialog_rejects_short_password(qtbot):
    dlg = CreateVaultDialog()
    qtbot.addWidget(dlg)
    dlg._password.setText("short")
    dlg._confirm.setText("short")
    dlg._on_accept()
    assert dlg.result() != QDialog.Accepted


def test_create_dialog_rejects_mismatch(qtbot):
    dlg = CreateVaultDialog()
    qtbot.addWidget(dlg)
    dlg._password.setText("longenough1")
    dlg._confirm.setText("different1")
    dlg._on_accept()
    assert dlg.result() != QDialog.Accepted


def test_unlock_dialog_wrong_then_right(qtbot, tmp_path):
    controller = VaultController(tmp_path / "vault.vault", kdf_params=KdfParams.create(**FAST))
    controller.create(PASSWORD)
    controller.lock()

    dlg = UnlockDialog(controller)
    qtbot.addWidget(dlg)
    dlg._password.setText("wrong")
    dlg._on_accept()
    assert dlg.result() != QDialog.Accepted
    assert not controller.is_unlocked

    dlg._password.setText(PASSWORD)
    dlg._on_accept()
    assert controller.is_unlocked


# --- main window -------------------------------------------------------
def test_main_window_lists_entries(qtbot, unlocked):
    controller, config = unlocked
    win = MainWindow(controller, config)
    qtbot.addWidget(win)
    assert win._list.count() == 2


def test_main_window_search_filters(qtbot, unlocked):
    controller, config = unlocked
    win = MainWindow(controller, config)
    qtbot.addWidget(win)
    win._search.setText("git")
    assert win._list.count() == 1


def test_main_window_reveal_password(qtbot, unlocked):
    controller, config = unlocked
    win = MainWindow(controller, config)
    qtbot.addWidget(win)
    win._list.setCurrentRow(0)
    assert win._d_password.text() == MASK
    win._reveal_btn.setChecked(True)
    assert win._d_password.text() == win._current.password


def test_main_window_delete_updates_list(qtbot, unlocked):
    controller, config = unlocked
    win = MainWindow(controller, config)
    qtbot.addWidget(win)
    win._list.setCurrentRow(0)
    # Delete directly via controller, then refresh (skips the modal confirm).
    controller.delete_entry(win._current.id)
    win._current = None
    win._refresh()
    assert win._list.count() == 1


def test_copy_arms_clipboard_clear_timer(qtbot, unlocked):
    controller, config = unlocked
    config.clipboard_clear_seconds = 15
    win = MainWindow(controller, config)
    qtbot.addWidget(win)
    win._copy("something")
    assert win._clip_timer.isActive()


def test_lock_sets_relock_flag(qtbot, unlocked):
    controller, config = unlocked
    win = MainWindow(controller, config)
    qtbot.addWidget(win)
    win._lock_now()
    assert win.relock_requested is True


def test_relock_disabled_when_auto_lock_zero(qtbot, unlocked):
    controller, config = unlocked
    config.auto_lock_minutes = 0
    win = MainWindow(controller, config)
    qtbot.addWidget(win)
    win._restart_lock_timer()
    assert not win._lock_timer.isActive()
