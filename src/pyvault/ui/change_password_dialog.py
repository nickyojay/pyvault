"""Change-master-password dialog."""

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
from pyvault.core.strength import password_strength
from pyvault.errors import InvalidPasswordError, VaultError
from pyvault.ui.unlock import MIN_PASSWORD_LEN


class ChangePasswordDialog(QDialog):
    """Prompt for the current + new master password and re-encrypt in place."""

    def __init__(self, controller: VaultController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self.setWindowTitle("Change Master Password")

        self._current = QLineEdit()
        self._current.setEchoMode(QLineEdit.Password)
        self._new = QLineEdit()
        self._new.setEchoMode(QLineEdit.Password)
        self._new.textChanged.connect(self._update_strength)
        self._confirm = QLineEdit()
        self._confirm.setEchoMode(QLineEdit.Password)

        self._strength = QLabel("")
        self._error = QLabel()
        self._error.setStyleSheet("color: #b00020;")

        form = QFormLayout()
        form.addRow("Current password", self._current)
        form.addRow("New password", self._new)
        form.addRow("", self._strength)
        form.addRow("Confirm new", self._confirm)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._error)
        layout.addWidget(buttons)

    def _update_strength(self, text: str) -> None:
        self._strength.setText(f"Strength: {password_strength(text)}" if text else "")

    def _on_accept(self) -> None:
        new = self._new.text()
        if len(new) < MIN_PASSWORD_LEN:
            self._error.setText(f"New password must be at least {MIN_PASSWORD_LEN} characters.")
            return
        if new != self._confirm.text():
            self._error.setText("New passwords do not match.")
            return
        try:
            self._controller.change_password(self._current.text(), new)
        except InvalidPasswordError:
            self._error.setText("Current master password is incorrect.")
            return
        except VaultError as exc:
            self._error.setText(str(exc))
            return
        self.accept()
