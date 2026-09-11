# VisManager

Review images across a folder tree, mark each one Keep or Delete, then
batch-convert the keepers to PDF and remove the rest.

Supports **TGA, PNG, JPEG, BMP, GIF, WebP, TIFF, ICO, DDS and PDF**.

---

## Quick start

### Run from source

```bat
pip install -r requirements.txt
python vismanager.py
```

### Build a standalone .exe

Double-click **`build_windows.bat`**, or run:

```powershell
python -m pip install -r requirements.txt
python -m PyInstaller vismanager.spec --clean
```

Output: **`dist\VisManager.exe`** — a single self-contained file you can copy
anywhere.

> The module is `PyInstaller` with a capital P and I. `python -m pyinstaller`
> in lowercase fails with `ModuleNotFoundError` even after a correct install.

### Build a Setup.exe installer

Install [Inno Setup](https://jrsoftware.org/isdl.php), then right-click
**`installer.iss`** → Compile. Produces
`installer_output\VisManager-Setup-1.0.0.exe` with a Start Menu entry,
optional desktop shortcut, optional `.tga` association, and an uninstaller.

---

## What's in this package

| File | Purpose |
|---|---|
| `vismanager.py` | The application — single file, no imports from the others |
| `vismanager.spec` | PyInstaller build recipe |
| `build_windows.bat` | One-click Windows build |
| `installer.iss` | Inno Setup script for a proper installer |
| `requirements.txt` | Pinned dependencies |
| `assets/vismanager.ico` | 7-resolution Windows icon (16→256 px) |
| `BUILDING.md` | Packaging details and troubleshooting |

The toolbar logo, wordmark and all button icons are **base64-embedded in
`vismanager.py`**, so the app is fully branded even if `assets/` is absent.
`assets/icons/` holds the extracted 18px glyphs for reference only. The `.ico` is needed
only at build time.

---

## Using it

1. **Open Directory** — scans every subfolder for supported files
2. Mark each file **Keep** (`K`) or **Delete** (`D`); `Space` toggles
3. **Process Images** — choose PDF layout and per-type deletion, then run

### Controls

| Action | Key | Action | Key |
|---|---|---|---|
| Keep / Delete | `K` / `D` | Zoom in / out | `=` / `-` |
| Toggle | `Space` | Zoom fit / 1:1 | `0` / `9` |
| Next / Prev image | `→` / `←` | Nav mode | `W` |
| Next / Prev folder | `Ctrl+→` / `Ctrl+←` | Preload mode | `P` |
| Keep / Delete all in folder | `Ctrl+K` / `Ctrl+D` | Open directory | `Ctrl+O` |
| Invert folder | `Ctrl+I` | Process | `Ctrl+P` |
| Add / edit note | `N` | Toggle flag | `F` |
| Export notes | `Ctrl+E` | Reset orientation | `R` |
| Rotate left / right | `[` / `]` | Flip horiz / vert | `H` / `V` |

**Every shortcut is rebindable** — click ⌨ Shortcuts, click a key, press the
new one. Saved to `~/.vismanager.json`.

### Features worth knowing

**Zoom** — scroll to zoom, drag to pan, double-click toggles fit ↔ 1:1. Only
the visible region is rendered, so deep zoom on a large texture costs no more
memory than the canvas.

**Navigation mode** (`W`) — *Continuous* runs off the end of a folder into the
next one; *Wrap* stays inside the current folder.

**Preload mode** (`P`) — *Whole folder* decodes everything up front on a
background thread with a progress readout, so browsing is instant afterwards.
*One at a time* decodes on demand. Worth enabling for PDF-heavy folders.

**Type filter** — the sidebar lists only the types actually found, each with a
count. Hiding a type preserves its Keep/Delete marks.

**Per-type deletion** — the Process dialog controls each file type separately,
so you can delete marked TGAs while protecting PNGs and PDFs entirely.

**Quit confirmation** — closing the window asks first, and warns if you have
flagged files whose notes were never exported to a `.txt`, offering to export
on the way out. It also reminds you that files marked DELETE are untouched
until you run Process.

**Rotate and flip** — `[` and `]` rotate, `H` and `V` flip, `R` resets. The
orientation is per file, survives restarts, and is **applied to the exported
PDF**, so what you see is what gets converted. Zoom is preserved while
rotating so you don't lose your place inspecting a detail.

**Flags and notes** — press `N` to write a note on any file, or `F` to flag it
without typing. Flags are independent of Keep/Delete, so you can annotate a
file you're keeping *and* one you're discarding. Flagged counts appear in the
folder list and toolbar. **Export Notes** (`Ctrl+E`) writes a plain-text report
grouped by folder, listing each flagged file, its Keep/Delete status, and its
note.

Notes and orientations are stored in `.vismanager_notes.json` **inside the folder you opened**,
not in your user profile, with paths kept relative — move or copy the asset
folder and the annotations travel with it.

---

## PDF previews

| Installed | Preview quality |
|---|---|
| `pypdf` only (default) | Extracts the embedded page image — exact for image-based and scanned PDFs, including every PDF VisManager makes |
| `+ pypdfium2` | Full rasteriser, handles vector and text-only PDFs too |

The sidebar shows which backend is live. PDFs that can't be previewed still
display a labelled card and remain fully markable.

`pypdfium2` ships a native binary PyInstaller doesn't detect on its own —
`vismanager.spec` collects it explicitly. See `BUILDING.md`.

---

## Requirements

- Python 3.9+
- Pillow, pypdf (see `requirements.txt`)
- tkinter — bundled with the python.org installer on Windows/macOS; on
  Debian/Ubuntu run `sudo apt install python3-tk`

Settings live in `~/.vismanager.json`. An older `~/.tga_reviewer_keys.json`
is migrated automatically on first run.
