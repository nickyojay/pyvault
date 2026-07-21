"""GUI entry point: wires config + controller and runs the unlock→main loop."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from pyvault.core.config import Config
from pyvault.core.controller import VaultController
from pyvault.errors import VaultError
from pyvault.ui.main_window import MainWindow
from pyvault.ui.unlock import CreateVaultDialog, UnlockDialog


def _run_unlock(controller: VaultController) -> bool:
    """Show the create-or-unlock dialog. Returns True once the vault is open."""
    if not controller.vault_exists():
        dlg = CreateVaultDialog()
        if dlg.exec() != QDialog.Accepted:
            return False
        try:
            controller.create(dlg.password())
        except VaultError as exc:
            QMessageBox.critical(None, "Could not create vault", str(exc))
            return False
        return True

    dlg = UnlockDialog(controller)
    return dlg.exec() == QDialog.Accepted


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    config = Config.load()
    controller = VaultController(config.vault_path)

    while True:
        # A settings change may have repointed the vault; keep them in sync.
        if str(controller.path) != config.vault_path:
            controller.set_path(config.vault_path)

        if not _run_unlock(controller):
            return 0

        window = MainWindow(controller, config)
        window.show()
        app.exec()

        if not window.relock_requested:
            return 0  # user closed/quit the window
        controller.lock()  # locked (manually or by timeout); loop back to unlock

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
