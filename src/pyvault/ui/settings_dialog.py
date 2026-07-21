"""Settings dialog: vault location and security timeouts."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pyvault.core.config import Config


class SettingsDialog(QDialog):
    """Edit and return updated application settings."""

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(480, 180)

        self._vault_path = QLineEdit(config.vault_path)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self._vault_path, 1)
        path_row.addWidget(browse)

        self._auto_lock = QSpinBox()
        self._auto_lock.setRange(0, 240)
        self._auto_lock.setSuffix(" min (0 = never)")
        self._auto_lock.setValue(config.auto_lock_minutes)

        self._clipboard = QSpinBox()
        self._clipboard.setRange(0, 300)
        self._clipboard.setSuffix(" s (0 = never clear)")
        self._clipboard.setValue(config.clipboard_clear_seconds)

        form = QFormLayout()
        form.addRow("Vault file", path_row)
        form.addRow("Auto-lock", self._auto_lock)
        form.addRow("Clear clipboard after", self._clipboard)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Select vault file", self._vault_path.text(), "Vault files (*.vault)"
        )
        if path:
            self._vault_path.setText(path)

    def apply_to(self, config: Config) -> Config:
        """Return a Config updated with the dialog's values."""
        config.vault_path = self._vault_path.text().strip()
        config.auto_lock_minutes = self._auto_lock.value()
        config.clipboard_clear_seconds = self._clipboard.value()
        return config
