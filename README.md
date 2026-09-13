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

## Opening files

**Drag and drop** folders (or files, which open their containing folder) onto
the window. If something is already open you are asked whether to add to the
list or replace it. With several directories open the sidebar groups folders
under a header per directory, and clicking a header collapses that group so a
large list stays readable.

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
| Fullscreen | `F11` | Help | `F1` |

Fullscreen keeps a compact control strip with navigation, Keep/Delete/Flag,
rotate, flip and zoom, plus a **Screen size / Window size** toggle — fill the
whole display, or just the current window.
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

## Generating cube files (optional)

**Make Cubes** in the toolbar (`Ctrl+G`) converts quantum-chemistry output in
the open directories into the `.cube` files this app displays:

```
.gbw  --orca_2mkl-->  .molden.input  --pyscf-->  HOMO/LUMO cubes
.gbw  --orca_plot-->  spin / electron density cube
```

Pressing it scans and shows exactly what it found — every `.gbw`,
`.molden` / `.molden.input` and `.scfp` / `.scfr` / `.densities` file, what
each can produce, and which cubes already sit beside it. It also reports which
parts of the toolchain are present, so a missing tool is visible before you
start rather than halfway through a batch.

Requirements: `pip install pyscf` for orbital cubes; `orca_2mkl` and
`orca_plot` on PATH (they ship with ORCA) for the `.gbw` and density stages.

Restricted vs unrestricted is read from the molden file itself, so open-shell
systems produce ALPHA/BETA sets automatically without being listed anywhere.
Grid size is selectable — note the cost scales with its cube, so 300³ is about
50x the work of 80³.

## 3D cube files (optional)

Install VTK to open Gaussian `.cube` files directly:

```bash
pip install vtk
```

Cube files then render as interactive isosurfaces — drag to orbit, scroll to
zoom.

**Isosurface and rendering** (`I`) covers isovalue, opacity, lobe and
background colours, atom colouring, and individual toggles for transparency
ordering, antialiasing, ambient occlusion and shadows — with **Apply as
default** to reuse the look on later files and **Reset** to return to it.

Atom colours can be set **per element** — only the elements present in the
open file are listed — on top of the whole-molecule schemes.

Shadows work with a positional key light, a 2048 shadow map and an ambient
term; VTK exposes no depth bias, so those are the levers. One caveat the
dialog states: the shadow pass cannot draw translucent geometry, so opacity is
held at 100% while shadows are on.

**Render quality** has three presets in the isosurface dialog:

| Preset | What it adds | Cost (software GL) |
|---|---|---|
| Fast | three-point lighting | ~106 ms/frame |
| Quality *(default)* | + depth peeling, FXAA | ~104 ms/frame |
| Best | + screen-space ambient occlusion | ~142 ms/frame |

Depth peeling matters most: without it two overlapping translucent lobes blend
in arbitrary order, which visibly shifts as you rotate. Shadow maps are
deliberately not offered — they drop translucent geometry entirely and band
opaque surfaces with self-shadowing artifacts.

**Isovalue** is front and centre: the left toolbar shows the current value with
`−` / `+` steppers, and `,` / `.` adjust it from the keyboard. Steps are
geometric rather than fixed, because cube values span orders of magnitude
between a diffuse tail and a nuclear cusp. `I` opens the full settings (isovalue, opacity, atoms/bonds, grid box,
smoothing); `Ctrl+3` opens **Export 3D View**:

| Output | Resolution |
|---|---|
| PNG, TIFF, JPEG | 1x – 8x multiplier on the view size |
| SVG, PDF, EPS | true vector, resolution-independent |

**Rendering quality** toggles live in the same dialog:

| Toggle | Effect | Cost |
|---|---|---|
| Ambient occlusion (SSAO) | contact shading in crevices | ~1x here, GPU-dependent |
| Shadows | cast shadows from a key light | ~1.2x |
| Order-correct transparency | fixes overlapping lobes | small |
| Anti-aliasing (FXAA) | smooths edges | negligible |

All four need OpenGL 3.2+; on a driver that can't manage the pass chain they
turn themselves back off rather than losing the picture. Settings persist and
carry across files.

There is a white-background option for publication figures and transparent
background for PNG/TIFF. Keep/Delete, flags and notes work on cube files just
like images.

Without VTK the app runs unchanged and simply ignores `.cube` files — worth
knowing because VTK is a ~500 MB dependency.

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
