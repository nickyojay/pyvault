"""Security-audit dialog: weak/reused (offline) + optional online breach check."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyvault.core import breach
from pyvault.core.controller import VaultController
from pyvault.errors import VaultError

_PRIVACY_NOTE = (
    "Offline checks (weak, reused) never leave your device. The online breach "
    "check queries Have I Been Pwned by sending only the first 5 characters of "
    "each password's SHA-1 hash — the passwords themselves are never transmitted."
)


class _BreachWorker(QThread):
    """Runs the online breach lookup off the UI thread."""

    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, controller: VaultController, fetch: breach.Fetcher | None) -> None:
        super().__init__()
        self._controller = controller
        self._fetch = fetch

    def run(self) -> None:
        try:
            self.done.emit(self._controller.check_all_breaches(fetch=self._fetch))
        except VaultError as exc:
            self.failed.emit(str(exc))


class AuditDialog(QDialog):
    """Show per-entry weak/reused flags and, on demand, breach counts."""

    COLUMNS = ["Title", "Weak", "Reused", "Breached"]

    def __init__(
        self,
        controller: VaultController,
        parent: QWidget | None = None,
        *,
        breach_fetch: breach.Fetcher | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._breach_fetch = breach_fetch
        self._worker: _BreachWorker | None = None
        self.setWindowTitle("Security Audit")
        self.resize(560, 420)

        self._rows = controller.audit()

        self._table = QTableWidget(len(self._rows), len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels(self.COLUMNS)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._populate()

        self._status = QLabel("")
        self._check_btn = QPushButton("Check for breaches online")
        self._check_btn.clicked.connect(self._start_breach_check)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        note = QLabel(_PRIVACY_NOTE)
        note.setWordWrap(True)

        buttons = QHBoxLayout()
        buttons.addWidget(self._status, 1)
        buttons.addWidget(self._check_btn)
        buttons.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self._table, 1)
        layout.addWidget(note)
        layout.addLayout(buttons)

    @staticmethod
    def _flag(value: bool) -> QTableWidgetItem:
        return QTableWidgetItem("⚠ yes" if value else "—")

    def _populate(self) -> None:
        for r, row in enumerate(self._rows):
            self._table.setItem(r, 0, QTableWidgetItem(row.entry.title))
            self._table.setItem(r, 1, self._flag(row.weak))
            self._table.setItem(r, 2, self._flag(row.reused))
            if row.pwned is None:
                pwned_text = "not checked"
            elif row.pwned:
                pwned_text = f"⚠ {row.pwned:,}×"
            else:
                pwned_text = "clean"
            self._table.setItem(r, 3, QTableWidgetItem(pwned_text))

    def _start_breach_check(self) -> None:
        self._check_btn.setEnabled(False)
        self._status.setText("Checking…")
        self._worker = _BreachWorker(self._controller, self._breach_fetch)
        self._worker.done.connect(self._on_breach_done)
        self._worker.failed.connect(self._on_breach_failed)
        self._worker.start()

    def _on_breach_done(self, counts: dict[str, int]) -> None:
        for row in self._rows:
            row.pwned = counts.get(row.entry.id, 0)
        self._populate()
        breached = sum(1 for row in self._rows if row.pwned)
        self._status.setText(
            f"Done — {breached} breached." if breached else "Done — none breached."
        )
        self._check_btn.setEnabled(True)

    def _on_breach_failed(self, message: str) -> None:
        self._status.setText(f"Failed: {message}")
        self._check_btn.setEnabled(True)
