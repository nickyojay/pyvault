"""Add / edit entry dialog."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyvault.core.model import Entry
from pyvault.core.strength import password_strength
from pyvault.ui.generator_dialog import GeneratorDialog


class EntryDialog(QDialog):
    """Create a new entry or edit an existing one."""

    def __init__(self, parent: QWidget | None = None, *, entry: Entry | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Entry" if entry else "New Entry")
        self.resize(420, 320)

        self._title = QLineEdit()
        self._username = QLineEdit()
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.Password)
        self._password.textChanged.connect(self._update_strength)
        self._strength = QLabel("")
        self._url = QLineEdit()
        self._notes = QPlainTextEdit()

        reveal = QPushButton("Show")
        reveal.setCheckable(True)
        reveal.toggled.connect(
            lambda on: self._password.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
        )
        generate = QPushButton("Generate…")
        generate.clicked.connect(self._generate)

        password_row = QHBoxLayout()
        password_row.addWidget(self._password, 1)
        password_row.addWidget(reveal)
        password_row.addWidget(generate)

        form = QFormLayout()
        form.addRow("Title *", self._title)
        form.addRow("Username", self._username)
        form.addRow("Password", password_row)
        form.addRow("", self._strength)
        form.addRow("URL", self._url)
        form.addRow("Notes", self._notes)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        if entry is not None:
            self._title.setText(entry.title)
            self._username.setText(entry.username)
            self._password.setText(entry.password)
            self._url.setText(entry.url)
            self._notes.setPlainText(entry.notes)

    def _update_strength(self, text: str) -> None:
        self._strength.setText(f"Strength: {password_strength(text)}" if text else "")

    def _generate(self) -> None:
        dlg = GeneratorDialog(self)
        if dlg.exec() == QDialog.Accepted and dlg.password():
            self._password.setText(dlg.password())

    def _on_accept(self) -> None:
        if not self._title.text().strip():
            QMessageBox.warning(self, "Missing title", "Title is required.")
            return
        self.accept()

    def values(self) -> dict[str, str]:
        return {
            "title": self._title.text().strip(),
            "username": self._username.text(),
            "password": self._password.text(),
            "url": self._url.text(),
            "notes": self._notes.toPlainText(),
        }
