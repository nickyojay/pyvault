"""Frozen-app entry point for PyInstaller (launches the GUI)."""

from pyvault.ui.app import main

if __name__ == "__main__":
    raise SystemExit(main())
