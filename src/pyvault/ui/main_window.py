"""Main application window: entry list, detail pane, and actions."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyvault.core.config import Config
from pyvault.core.controller import VaultController
from pyvault.core.model import Entry
from pyvault.errors import VaultError
from pyvault.ui.change_password_dialog import ChangePasswordDialog
from pyvault.ui.entry_dialog import EntryDialog
from pyvault.ui.settings_dialog import SettingsDialog

MASK = "••••••••"


class MainWindow(QMainWindow):
    """Displays the unlocked vault and mediates all edits via the controller."""

    def __init__(
        self,
        controller: VaultController,
        config: Config,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._config = config
        self._current: Entry | None = None
        self._password_revealed = False
        self.relock_requested = False

        self.setWindowTitle("PyVault")
        self.resize(760, 480)
        self._build_ui()
        self._build_menu()
        self._refresh()

        self._clip_timer = QTimer(self)
        self._clip_timer.setSingleShot(True)
        self._clip_timer.timeout.connect(self._clear_clipboard)

        self._lock_timer = QTimer(self)
        self._lock_timer.setSingleShot(True)
        self._lock_timer.timeout.connect(self._auto_lock)
        self._install_activity_filter()
        self._restart_lock_timer()

    # --- construction --------------------------------------------------
    def _build_ui(self) -> None:
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search…")
        self._search.textChanged.connect(self._refresh)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.currentItemChanged.connect(self._on_selection)

        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add)
        self._edit_btn = QPushButton("Edit")
        self._edit_btn.clicked.connect(self._edit)
        self._del_btn = QPushButton("Delete")
        self._del_btn.clicked.connect(self._delete)
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self._open_settings)
        lock_btn = QPushButton("Lock")
        lock_btn.clicked.connect(self._lock_now)

        left_buttons = QHBoxLayout()
        for btn in (add_btn, self._edit_btn, self._del_btn):
            left_buttons.addWidget(btn)

        left = QVBoxLayout()
        left.addWidget(self._search)
        left.addWidget(self._list, 1)
        left.addLayout(left_buttons)
        left_widget = QWidget()
        left_widget.setLayout(left)

        self._detail = self._build_detail()

        top = QHBoxLayout()
        top.addWidget(left_widget, 1)
        top.addWidget(self._detail, 1)

        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        toolbar.addWidget(settings_btn)
        toolbar.addWidget(lock_btn)

        root = QVBoxLayout()
        root.addLayout(top, 1)
        root.addLayout(toolbar)
        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)

    def _build_detail(self) -> QWidget:
        self._d_title = QLabel("—")
        self._d_username = QLabel("")
        self._d_url = QLabel("")
        self._d_password = QLabel(MASK)
        self._d_notes = QLabel("")
        self._d_notes.setWordWrap(True)

        copy_user = QPushButton("Copy")
        copy_user.clicked.connect(self._copy_username)
        copy_pass = QPushButton("Copy")
        copy_pass.clicked.connect(self._copy_password)
        self._reveal_btn = QPushButton("Show")
        self._reveal_btn.setCheckable(True)
        self._reveal_btn.toggled.connect(self._toggle_reveal)

        username_row = QHBoxLayout()
        username_row.addWidget(self._d_username, 1)
        username_row.addWidget(copy_user)
        password_row = QHBoxLayout()
        password_row.addWidget(self._d_password, 1)
        password_row.addWidget(self._reveal_btn)
        password_row.addWidget(copy_pass)

        form = QFormLayout()
        form.addRow(QLabel("<b>Title</b>"), self._d_title)
        form.addRow("Username", self._wrap(username_row))
        form.addRow("Password", self._wrap(password_row))
        form.addRow("URL", self._d_url)
        form.addRow("Notes", self._d_notes)

        detail = QWidget()
        detail.setLayout(form)
        return detail

    @staticmethod
    def _wrap(layout: QHBoxLayout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w

    def _build_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")
        file_menu.addAction("Import from CSV…", self._import_csv)
        file_menu.addAction("Export to CSV…", self._export_csv)
        file_menu.addSeparator()
        file_menu.addAction("Quit", self.close)

        vault_menu = menu.addMenu("&Vault")
        vault_menu.addAction("Change Master Password…", self._change_password)
        vault_menu.addAction("Settings…", self._open_settings)
        vault_menu.addAction("Lock", self._lock_now)

    # --- list / selection ---------------------------------------------
    def _refresh(self) -> None:
        selected_id = self._current.id if self._current else None
        self._list.clear()
        for entry in sorted(self._controller.search(self._search.text()), key=_sort_key):
            item = QListWidgetItem(entry.title)
            item.setData(Qt.UserRole, entry.id)
            self._list.addItem(item)
            if entry.id == selected_id:
                self._list.setCurrentItem(item)
        if self._list.currentItem() is None:
            self._show_entry(None)

    def _on_selection(self, current: QListWidgetItem | None) -> None:
        if current is None:
            self._show_entry(None)
            return
        entry_id = current.data(Qt.UserRole)
        self._show_entry(self._controller.get(entry_id))

    def _show_entry(self, entry: Entry | None) -> None:
        self._current = entry
        self._password_revealed = False
        self._reveal_btn.setChecked(False)
        has = entry is not None
        self._edit_btn.setEnabled(has)
        self._del_btn.setEnabled(has)
        self._d_title.setText(entry.title if has else "—")
        self._d_username.setText(entry.username if has else "")
        self._d_url.setText(entry.url if has else "")
        self._d_notes.setText(entry.notes if has else "")
        self._render_password()

    def _render_password(self) -> None:
        if self._current is None:
            self._d_password.setText(MASK)
        else:
            self._d_password.setText(self._current.password if self._password_revealed else MASK)

    def _toggle_reveal(self, on: bool) -> None:
        self._password_revealed = on
        self._render_password()

    # --- actions -------------------------------------------------------
    def _add(self) -> None:
        dlg = EntryDialog(self)
        if dlg.exec() == EntryDialog.Accepted:
            entry = self._controller.add_entry(**dlg.values())
            self._current = entry
            self._refresh()
            self._notify_conflict()

    def _edit(self) -> None:
        if self._current is None:
            return
        dlg = EntryDialog(self, entry=self._current)
        if dlg.exec() == EntryDialog.Accepted:
            self._controller.update_entry(self._current.id, **dlg.values())
            self._refresh()
            self._show_entry(self._controller.get(self._current.id))
            self._notify_conflict()

    def _delete(self) -> None:
        if self._current is None:
            return
        confirm = QMessageBox.question(self, "Delete entry", f"Delete {self._current.title!r}?")
        if confirm == QMessageBox.Yes:
            self._controller.delete_entry(self._current.id)
            self._current = None
            self._refresh()
            self._notify_conflict()

    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV files (*.csv)")
        if not path:
            return
        try:
            count = self._controller.import_csv(path)
        except VaultError as exc:
            QMessageBox.warning(self, "Import failed", str(exc))
            return
        self._refresh()
        self._notify_conflict()
        QMessageBox.information(self, "Import complete", f"Imported {count} entries.")

    def _export_csv(self) -> None:
        confirm = QMessageBox.warning(
            self,
            "Export plaintext?",
            "The exported CSV will contain your passwords in plaintext. Continue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV files (*.csv)")
        if not path:
            return
        self._controller.export_csv(path)
        QMessageBox.information(self, "Export complete", f"Exported to {path}.")

    def _change_password(self) -> None:
        dlg = ChangePasswordDialog(self._controller, self)
        if dlg.exec() == ChangePasswordDialog.Accepted:
            QMessageBox.information(self, "Done", "Master password changed.")

    def _notify_conflict(self) -> None:
        """Tell the user if a synced remote copy was preserved during save."""
        if self._controller.last_conflict_path is None:
            return
        preserved = self._controller.last_conflict_path
        self._controller.last_conflict_path = None
        QMessageBox.information(
            self,
            "Sync conflict preserved",
            "The vault had changed on disk (likely synced from another device). "
            f"That version was saved as:\n\n{preserved}\n\n"
            "Your change was applied. Review the preserved file if you need to merge.",
        )

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._config, self)
        if dlg.exec() != SettingsDialog.Accepted:
            return
        old_path = self._config.vault_path
        dlg.apply_to(self._config)
        self._config.save()
        self._restart_lock_timer()
        if self._config.vault_path != old_path:
            QMessageBox.information(
                self,
                "Vault path changed",
                "The new vault path takes effect after you lock and unlock.",
            )

    # --- clipboard -----------------------------------------------------
    def _copy_username(self) -> None:
        self._copy(self._current.username if self._current else "")

    def _copy_password(self) -> None:
        self._copy(self._current.password if self._current else "")

    def _copy(self, text: str) -> None:
        if not text:
            return
        QGuiApplication.clipboard().setText(text)
        seconds = self._config.clipboard_clear_seconds
        if seconds > 0:
            self._clip_timer.start(seconds * 1000)

    def _clear_clipboard(self) -> None:
        QGuiApplication.clipboard().clear()

    # --- locking / auto-lock ------------------------------------------
    def _install_activity_filter(self) -> None:
        self._activity_filter = _ActivityFilter(self._restart_lock_timer)
        app = QGuiApplication.instance()
        if app is not None:
            app.installEventFilter(self._activity_filter)

    def _restart_lock_timer(self) -> None:
        minutes = self._config.auto_lock_minutes
        if minutes > 0:
            self._lock_timer.start(minutes * 60 * 1000)
        else:
            self._lock_timer.stop()

    def _auto_lock(self) -> None:
        self._relock_and_close()

    def _lock_now(self) -> None:
        self._relock_and_close()

    def _relock_and_close(self) -> None:
        self.relock_requested = True
        self._clear_clipboard()
        self.close()


def _sort_key(entry: Entry) -> str:
    return entry.title.lower()


class _ActivityFilter(QObject):
    """Resets the auto-lock timer on user input events."""

    _RESET_EVENTS = frozenset(
        {
            QEvent.MouseButtonPress,
            QEvent.KeyPress,
            QEvent.Wheel,
        }
    )

    def __init__(self, on_activity) -> None:
        super().__init__()
        self._on_activity = on_activity

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() in self._RESET_EVENTS:
            self._on_activity()
        return False
