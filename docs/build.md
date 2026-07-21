# Building standalone PyVault binaries

PyVault ships as a single windowed executable per OS, built with
[PyInstaller](https://pyinstaller.org/) from [`pyvault.spec`](../pyvault.spec).
End users do **not** need Python installed.

## Prerequisites

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"          # includes pyinstaller
```

## Build

Run on the target OS (PyInstaller does not cross-compile):

```bash
pyinstaller pyvault.spec --clean --noconfirm
```

Output in `dist/`:

| OS | Artifact |
|----|----------|
| Linux | `dist/PyVault` (single executable) |
| Windows | `dist/PyVault.exe` |
| macOS | `dist/PyVault.app` (plus a raw `dist/PyVault`) |

CI builds all three automatically — see
[`.github/workflows/release.yml`](../.github/workflows/release.yml).

## Windows installer

For distribution on Windows, the raw `PyVault.exe` is wrapped in a proper
installer wizard with [Inno Setup](https://jrsoftware.org/isinfo.php) using
[`packaging/pyvault.iss`](../packaging/pyvault.iss). The installer:

- installs per-user (no administrator rights required),
- adds Start Menu (and optional desktop) shortcuts,
- registers a standard uninstaller.

Build it on Windows after the PyInstaller step:

```bat
pyinstaller pyvault.spec --clean --noconfirm
iscc packaging\pyvault.iss
```

Output: `packaging\dist_installer\PyVault-Setup.exe`. CI produces this
automatically and uploads it as the **PyVault-Windows-Installer** artifact.

### Linux runtime note

The Qt `xcb` platform plugin needs a few system libraries at run time. On
Debian/Ubuntu:

```bash
sudo apt install libxcb-cursor0
```

## Running an unsigned app

These binaries are **not code-signed** (signing requires paid Apple/Windows
certificates). For personal use you can bypass the OS warnings:

### macOS (Gatekeeper)

The first launch is blocked because the app isn't notarized. Either:

- Right-click the app → **Open** → **Open** in the dialog, or
- Clear the quarantine attribute:
  ```bash
  xattr -dr com.apple.quarantine /Applications/PyVault.app
  ```

Proper distribution would require an Apple Developer ID signature + notarization.

### Windows (SmartScreen)

"Windows protected your PC" → **More info** → **Run anyway**. Proper
distribution would require an Authenticode code-signing certificate.

### Linux

Mark it executable and run it:

```bash
chmod +x PyVault
./PyVault
```

(An AppImage is a good future option for wider Linux distribution.)
