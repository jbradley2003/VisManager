# Building VisManager as an executable

## You cannot build a .exe on a Mac

PyInstaller does **not** cross-compile. It bundles the Python interpreter and
libraries belonging to the machine it runs on:

| Built on | Output format | Runs on |
|---|---|---|
| Windows | PE/COFF `.exe` | Windows, and Wine |
| macOS | Mach-O | macOS only |
| Linux | ELF | Linux only |

Wine is a loader for Windows PE executables. A macOS build is Mach-O, so Wine
has nothing it can load — there is no flag or setting that changes this.

### Three ways to get a real .exe

**1. GitHub Actions (no Windows machine needed)**

`.github/workflows/build.yml` is included. Push the repo to GitHub, open the
Actions tab, and run "Build VisManager". A Windows runner builds it and you
download `VisManager.exe` as an artifact, usually in about three minutes.
This is free for public repos and has a generous free tier for private ones.

**2. A Windows VM on your Mac**

Parallels, VMware Fusion, or UTM (free). Install Python, then run
`build_windows.bat` inside the VM.

**3. Build Python-under-Wine on macOS**

Technically possible — install the Windows Python installer inside Wine and
run PyInstaller with it — but tkinter under Wine is unreliable and this is
the most fragile option. Not recommended for a GUI app.

### Building for macOS itself

If you want to run it on your Mac, you don't need Wine at all. Build normally
and the spec produces `dist/VisManager.app`, a proper bundle with the icon:

```bash
python3 -m pip install -r requirements.txt
python3 -m PyInstaller vismanager.spec --clean
open dist/VisManager.app
```

Unsigned apps are blocked by Gatekeeper on first launch. Right-click the app
and choose **Open**, or run
`xattr -dr com.apple.quarantine dist/VisManager.app`.

---


## The pypdfium2 problem

`pypdfium2` ships a **native binary** (`pdfium.dll` on Windows) inside the
separate `pypdfium2_raw` package. PyInstaller's dependency scanner only
follows Python imports, so it never sees that DLL and silently leaves it out.

The result is the worst kind of failure: the frozen app imports `pypdfium2`
without complaint, then crashes the first time it opens a PDF.

Two independent defences are now in place, so you can go either way.

---

## Option A — Pure Python (recommended, zero packaging risk)

```bat
pip install pillow pypdf pyinstaller
```

Open `vismanager.spec` and set:

```python
INCLUDE_PDFIUM = False
```

Then:

```bat
pyinstaller vismanager.spec --clean
```

`pypdf` is pure Python, so there is no binary to lose. PDF previews use
**embedded-image extraction**: the app pulls the largest image out of page 1.

- Exact for image-derived PDFs — including every PDF this app produces, and
  virtually all scanned documents.
- Cannot preview vector/text-only PDFs. Those show a labelled placeholder and
  are still fully markable as Keep or Delete.

The sidebar displays `PDF: embedded-image mode` so this is never a mystery.

---

## Option B — Full renderer

```bat
pip install pillow pypdf pypdfium2 pyinstaller
pyinstaller vismanager.spec --clean
```

Leave `INCLUDE_PDFIUM = True`. The spec calls `collect_dynamic_libs()` on
`pypdfium2_raw` to force the native binary into the bundle.

Watch the build output for confirmation:

```
[spec] pypdfium2 native libs collected: ['pdfium.dll']
```

If you instead see `WARNING: no pypdfium2 binary found`, the DLL was not
located — the exe will still work via the pypdf fallback.

---

## Why the app can't be fooled

`_resolve_pdf_backend()` doesn't just try to import each backend, it **probes**
`pypdfium2.PdfDocument` before committing. A half-bundled install therefore
falls through to `pypdf` instead of crashing at runtime.

Verified inside a real frozen executable:

| Build | pypdfium2 | pypdf | PDF preview | Size |
|---|---|---|---|---|
| `INCLUDE_PDFIUM = True` | renders | available | full renderer | ~44 MB |
| `INCLUDE_PDFIUM = False` | excluded | available | embedded-image | ~36 MB |

---

## Pillow plugin note

The spec lists every Pillow codec in `hiddenimports`. Pillow registers formats
dynamically, so PyInstaller can't detect them. Without those entries you get
`cannot identify image file` for `.tga` and `.dds` **only in the packaged
build** — it works fine from source, which makes it a confusing bug to chase.

---

## Branding assets

`assets/vismanager.ico` is a 7-resolution Windows icon (16 → 256 px) generated
from the logo. The spec references it via `icon="assets/vismanager.ico"`, so
keep the `assets/` folder next to the spec when building.

The toolbar logo and wordmark are **base64-embedded inside `vismanager.py`**
rather than shipped as data files. There is nothing for PyInstaller to miss, so
a packaged build can never come up unbranded. Adds ~16 KB to the script.

If you build on Linux you'll see `WARNING: Ignoring icon; supported only on
Windows and macOS` — expected and harmless.

---

## Other flags

- `console=False` hides the terminal window. Flip it to `True` temporarily if
  you need to see a traceback from the packaged app.
- `upx=False` is deliberate. UPX compression is known to corrupt `pdfium.dll`.
- Add `icon="icon.ico"` to the `EXE()` block for a custom icon.

---

## Quick sanity check after building

Run the exe, open a folder containing a PDF, and look at the sidebar under
FILE TYPES:

- `PDF: pypdfium2` — full renderer bundled correctly
- `PDF: embedded-image mode` — pypdf fallback active
- `⚠ no PDF preview` — neither made it in; check the build log
