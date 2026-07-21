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

from pyvault.ui.audit_dialog import AuditDialog  # noqa: E402
from pyvault.ui.change_password_dialog import ChangePasswordDialog  # noqa: E402
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


def test_entry_dialog_shows_password_strength(qtbot):
    dlg = EntryDialog()
    qtbot.addWidget(dlg)
    assert dlg._strength.text() == ""  # empty until typed
    dlg._password.setText("Xy7!Xy7!Xy7!Xy7!")
    assert "Strong" in dlg._strength.text()
    dlg._password.setText("weak")
    assert "Weak" in dlg._strength.text()


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


# --- change password dialog -------------------------------------------
def test_change_password_dialog_wrong_then_right(qtbot, unlocked):
    controller, _ = unlocked
    dlg = ChangePasswordDialog(controller)
    qtbot.addWidget(dlg)

    dlg._current.setText("wrong-current")
    dlg._new.setText("new-master-pass-1")
    dlg._confirm.setText("new-master-pass-1")
    dlg._on_accept()
    assert dlg.result() != QDialog.Accepted

    dlg._current.setText(PASSWORD)
    dlg._on_accept()
    assert dlg.result() == QDialog.Accepted
    controller.lock()
    controller.unlock("new-master-pass-1")  # new password now works


def test_change_password_dialog_rejects_mismatch(qtbot, unlocked):
    controller, _ = unlocked
    dlg = ChangePasswordDialog(controller)
    qtbot.addWidget(dlg)
    dlg._current.setText(PASSWORD)
    dlg._new.setText("new-master-pass-1")
    dlg._confirm.setText("different-9")
    dlg._on_accept()
    assert dlg.result() != QDialog.Accepted


def test_create_dialog_shows_strength(qtbot):
    dlg = CreateVaultDialog()
    qtbot.addWidget(dlg)
    dlg._password.setText("Xy7!Xy7!Xy7!Xy7!")
    assert "Strong" in dlg._strength.text()


# --- security audit dialog --------------------------------------------
def test_audit_dialog_shows_offline_flags(qtbot, tmp_path):
    controller = VaultController(tmp_path / "vault.vault", kdf_params=KdfParams.create(**FAST))
    controller.create(PASSWORD)
    controller.add_entry(title="Weak", password="weak")
    controller.add_entry(title="Strong", password="Xy7!Xy7!Xy7!Xy7!")

    dlg = AuditDialog(controller)
    qtbot.addWidget(dlg)
    # Column 1 is "Weak"; the weak entry should be flagged, the strong one not.
    titles = {dlg._table.item(r, 0).text(): r for r in range(dlg._table.rowCount())}
    assert "yes" in dlg._table.item(titles["Weak"], 1).text()
    assert dlg._table.item(titles["Strong"], 1).text() == "—"


def test_audit_dialog_online_breach_check(qtbot, tmp_path):
    import hashlib

    controller = VaultController(tmp_path / "vault.vault", kdf_params=KdfParams.create(**FAST))
    controller.create(PASSWORD)
    controller.add_entry(title="Site", password="password123")

    suffix = hashlib.sha1(b"password123", usedforsecurity=False).hexdigest().upper()[5:]

    def fake_fetch(_prefix):
        return f"{suffix}:5000\n"

    dlg = AuditDialog(controller, breach_fetch=fake_fetch)
    qtbot.addWidget(dlg)
    row = next(r for r in range(dlg._table.rowCount()) if dlg._table.item(r, 0).text() == "Site")
    dlg._start_breach_check()
    qtbot.waitUntil(lambda: "5,000" in dlg._table.item(row, 3).text(), timeout=3000)
