# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for image_reviewer.py

Build:
    pyinstaller image_reviewer.spec --clean

Produces a single-file executable in dist/.

────────────────────────────────────────────────────────────────────────────
Why this spec exists
────────────────────────────────────────────────────────────────────────────
pypdfium2 ships a NATIVE binary (pdfium.dll / .so / .dylib) inside the
pypdfium2_raw package.  PyInstaller's dependency scanner only follows Python
imports, so it does not see that binary and silently omits it.  The frozen
app then imports pypdfium2 successfully but crashes the moment it tries to
open a document.

Two defences are in place:

  1. This spec explicitly collects pypdfium2's binary and metadata, so the
     good renderer works in the packaged app.

  2. image_reviewer.py falls back to pypdf — pure Python, nothing to
     collect — if pypdfium2 is missing or non-functional.  It probes
     pypdfium2 for real before committing to it, so a half-bundled install
     degrades to the fallback instead of crashing.

If you would rather not deal with native binaries at all, set
INCLUDE_PDFIUM = False below and install only pypdf.  PDF previews then use
embedded-image extraction, which is exact for image-derived PDFs (including
every PDF this app produces) and unavailable for vector/text PDFs.
"""

INCLUDE_PDFIUM = True     # set False for a pure-Python, pypdf-only build

# ── Cross-compiling is not possible ───────────────────────────────────────
# PyInstaller bundles the interpreter and libraries of the HOST platform:
#   built on Windows -> PE .exe   (runs on Windows, and under Wine)
#   built on macOS   -> Mach-O    (runs on macOS only — Wine cannot load it)
#   built on Linux   -> ELF       (runs on Linux only)
# To get a .exe you must build on Windows. If you don't have a Windows
# machine, .github/workflows/build.yml runs the build on a free GitHub
# Actions Windows runner and hands you the artifact.

import os
import sys
from PyInstaller.utils.hooks import collect_dynamic_libs, copy_metadata

binaries = []
datas = []

# The logo and wordmark are base64-embedded in the .py, so no data files are
# needed at runtime. assets/vismanager.ico is used only at build time for the
# Windows executable icon.
excludes = [
    # Trim heavy libs the app never touches. Remove entries if you add
    # features that need them.
    "matplotlib", "numpy.f2py", "scipy", "pandas",
    "PyQt5", "PyQt6", "PySide2", "PySide6",
    "IPython", "jupyter", "notebook", "pytest",
]
hiddenimports = [
    # Pillow format plugins are imported dynamically by the codec registry,
    # so PyInstaller cannot see them. Without these, opening a .tga or .dds
    # raises "cannot identify image file" only in the packaged build.
    "PIL._tkinter_finder",
    "PIL.TgaImagePlugin",
    "PIL.PngImagePlugin",
    "PIL.JpegImagePlugin",
    "PIL.BmpImagePlugin",
    "PIL.GifImagePlugin",
    "PIL.WebPImagePlugin",
    "PIL.TiffImagePlugin",
    "PIL.IcoImagePlugin",
    "PIL.DdsImagePlugin",
    "PIL.PdfImagePlugin",
]

# ── PDF backends ──────────────────────────────────────────────────────────
# pypdf: pure Python, nothing special needed.
try:
    import pypdf  # noqa: F401
    hiddenimports += ["pypdf"]
    print("[spec] pypdf found — pure-Python PDF fallback included")
except ImportError:
    print("[spec] WARNING: pypdf not installed. Run: pip install pypdf")

# pypdfium2: needs its native library collected by hand.
if INCLUDE_PDFIUM:
    try:
        import pypdfium2  # noqa: F401
        libs = collect_dynamic_libs("pypdfium2_raw")
        libs += collect_dynamic_libs("pypdfium2")
        if libs:
            binaries += libs
            print(f"[spec] pypdfium2 native libs collected: "
                  f"{[b[0].split('/')[-1] for b in libs]}")
        else:
            print("[spec] WARNING: no pypdfium2 binary found; "
                  "the exe will fall back to pypdf")
        hiddenimports += ["pypdfium2", "pypdfium2_raw"]
        for pkg in ("pypdfium2", "pypdfium2_raw"):
            try:
                datas += copy_metadata(pkg)
            except Exception:
                pass
    except ImportError:
        print("[spec] pypdfium2 not installed — skipping (pypdf will be used)")
else:
    # PyInstaller ships its own pypdfium2 hook, so the package sneaks into the
    # bundle even when we don't ask for it. Exclude it explicitly to get a
    # genuinely pure-Python build.
    excludes += ["pypdfium2", "pypdfium2_raw"]
    print("[spec] INCLUDE_PDFIUM=False — pypdfium2 excluded, pypdf only")


# Pick the icon format the host platform actually accepts. Windows wants
# .ico, macOS wants .icns; passing the wrong one is ignored with a warning.
if sys.platform == "darwin" and os.path.exists("assets/vismanager.icns"):
    APP_ICON = "assets/vismanager.icns"
elif os.path.exists("assets/vismanager.ico"):
    APP_ICON = "assets/vismanager.ico"
else:
    APP_ICON = None

a = Analysis(
    ["vismanager.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="VisManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX can corrupt pdfium.dll — leave it off
    runtime_tmpdir=None,
    console=False,      # set True temporarily if you need to see tracebacks
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=APP_ICON,
)

# On macOS, wrap the executable in a proper .app bundle so Finder and the
# Dock show the icon and name instead of a bare unix executable.
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="VisManager.app",
        icon=APP_ICON,
        bundle_identifier="com.vismanager.reviewer",
        info_plist={
            "CFBundleName": "VisManager",
            "CFBundleDisplayName": "VisManager",
            "CFBundleShortVersionString": "1.3.0",
            "NSHighResolutionCapable": True,
        },
    )
