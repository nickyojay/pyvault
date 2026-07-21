# PyInstaller spec for PyVault — builds a standalone, single-file GUI app.
# Usage: pyinstaller pyvault.spec --clean --noconfirm
#
# Produces a windowed (no-console) binary in dist/:
#   - Linux:   dist/PyVault
#   - Windows: dist/PyVault.exe
#   - macOS:   dist/PyVault.app  (and a raw dist/PyVault executable)

import sys

APP_NAME = "PyVault"

a = Analysis(
    ["packaging/entry.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    # The core crypto libs are imported dynamically enough that we pin them;
    # PySide6's own PyInstaller hook bundles the Qt runtime + platform plugins.
    hiddenimports=["argon2", "cryptography"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.Qt3D"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed app, no terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name=f"{APP_NAME}.app",
        icon=None,
        bundle_identifier="com.pyvault.app",
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "NSHighResolutionCapable": True,
        },
    )
