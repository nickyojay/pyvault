"""Create-vault and unlock dialogs shown before the main window."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from pyvault.core.controller import VaultController
from pyvault.errors import InvalidPasswordError, VaultError

MIN_PASSWORD_LEN = 8


class CreateVaultDialog(QDialog):
    """Prompt for a new master password (with confirmation)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Vault")

        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.Password)
        self._confirm = QLineEdit()
        self._confirm.setEchoMode(QLineEdit.Password)
        self._error = QLabel()
        self._error.setStyleSheet("color: #b00020;")

        form = QFormLayout()
        form.addRow("New master password", self._password)
        form.addRow("Confirm", self._confirm)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Choose a strong master password. It cannot be recovered."))
        layout.addLayout(form)
        layout.addWidget(self._error)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        pw = self._password.text()
        if len(pw) < MIN_PASSWORD_LEN:
            self._error.setText(f"Password must be at least {MIN_PASSWORD_LEN} characters.")
            return
        if pw != self._confirm.text():
            self._error.setText("Passwords do not match.")
            return
        self.accept()

    def password(self) -> str:
        return self._password.text()


class UnlockDialog(QDialog):
    """Prompt for the master password and unlock the vault in place.

    Stays open and shows an error on a wrong password; only accepts on success.
    """

    def __init__(self, controller: VaultController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self.setWindowTitle("Unlock Vault")

        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.Password)
        self._error = QLabel()
        self._error.setStyleSheet("color: #b00020;")

        form = QFormLayout()
        form.addRow("Master password", self._password)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Unlocking {controller.path}"))
        layout.addLayout(form)
        layout.addWidget(self._error)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        try:
            self._controller.unlock(self._password.text())
        except InvalidPasswordError:
            self._error.setText("Invalid master password (or the vault was modified).")
            self._password.clear()
            self._password.setFocus()
            return
        except VaultError as exc:
            self._error.setText(str(exc))
            return
        self.accept()
