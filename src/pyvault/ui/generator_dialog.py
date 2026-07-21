"""Password generator dialog."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pyvault.core.generator import generate_password


class GeneratorDialog(QDialog):
    """Configure and preview a generated password; returns it on accept."""

    def __init__(self, parent: QWidget | None = None, *, length: int = 20) -> None:
        super().__init__(parent)
        self.setWindowTitle("Generate Password")

        self._length = QSpinBox()
        self._length.setRange(4, 128)
        self._length.setValue(length)
        self._upper = QCheckBox("Uppercase (A-Z)")
        self._digits = QCheckBox("Digits (0-9)")
        self._symbols = QCheckBox("Symbols (!@#…)")
        self._ambiguous = QCheckBox("Avoid ambiguous characters")
        for box in (self._upper, self._digits, self._symbols):
            box.setChecked(True)

        self._output = QLineEdit()
        self._output.setReadOnly(True)

        form = QFormLayout()
        form.addRow("Length", self._length)
        form.addRow(self._upper)
        form.addRow(self._digits)
        form.addRow(self._symbols)
        form.addRow(self._ambiguous)
        form.addRow("Password", self._output)

        regenerate = QPushButton("Regenerate")
        regenerate.clicked.connect(self.regenerate)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        button_row = QHBoxLayout()
        button_row.addWidget(regenerate)
        button_row.addStretch(1)
        button_row.addWidget(buttons)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(button_row)

        for widget in (self._length, self._upper, self._digits, self._symbols, self._ambiguous):
            signal = widget.toggled if isinstance(widget, QCheckBox) else widget.valueChanged
            signal.connect(self.regenerate)

        self.regenerate()

    def regenerate(self) -> None:
        try:
            self._output.setText(
                generate_password(
                    self._length.value(),
                    upper=self._upper.isChecked(),
                    digits=self._digits.isChecked(),
                    symbols=self._symbols.isChecked(),
                    avoid_ambiguous=self._ambiguous.isChecked(),
                )
            )
        except ValueError as exc:
            self._output.setText(f"<{exc}>")

    def password(self) -> str:
        return self._output.text()
