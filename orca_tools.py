"""
Turn quantum-chemistry output into cube files VisManager can display.

Two stages, either of which can be run on its own:

    .gbw  --orca_2mkl-->  .molden.input  --pyscf cubegen-->  *.cube
    .gbw  --orca_plot-->  spin density / electron density .cube

Both stages are optional at runtime. orca_2mkl and orca_plot ship with ORCA
and must be on PATH; pyscf is a pip install. Whatever is missing is reported
in the dialog rather than failing halfway through a batch.

Adapted from a working batch script, with two behavioural changes:

  * Restricted vs unrestricted is detected from the molden file itself (the
    shape of mo_occ) instead of being hard-coded per system name. Hard-coding
    silently produces the wrong orbitals the moment a new system is added.
  * Every step reports through a callback, so a long batch can show progress
    and be cancelled, instead of blocking with no feedback.
"""

import os
import shutil
import subprocess
import sys
import tempfile

# What each stage needs
ORCA_2MKL = "orca_2mkl"
ORCA_PLOT = "orca_plot"

GBW_EXTS = {".gbw"}
MOLDEN_EXTS = {".molden", ".input"}      # ORCA writes <name>.molden.input
# ORCA density files. .scfp/.scfr are SCF densities, .densities is the newer
# container; orca_plot reads them alongside the matching .gbw.
DENSITY_EXTS = {".scfp", ".scfr", ".densities"}


def _which(name):
    return shutil.which(name) or shutil.which(name + ".exe")


def orca_available():
    return _which(ORCA_2MKL) is not None


def orca_plot_available():
    return _which(ORCA_PLOT) is not None


def pyscf_available():
    try:
        import pyscf  # noqa: F401
        from pyscf.tools import molden, cubegen  # noqa: F401
        return True
    except Exception:
        return False


def backend_report():
    """One line per dependency, for the dialog."""
    rows = []
    rows.append(("orca_2mkl", orca_available(),
                 ".gbw to molden — ships with ORCA, must be on PATH"))
    rows.append(("orca_plot", orca_plot_available(),
                 "spin/electron density cubes — ships with ORCA"))
    rows.append(("pyscf", pyscf_available(),
                 "molden to orbital cubes — pip install pyscf"))
    return rows


def is_molden(path):
    low = path.lower()
    return low.endswith(".molden") or low.endswith(".molden.input")


def classify(path):
    """What kind of source file this is, or None."""
    low = path.lower()
    ext = os.path.splitext(low)[1]
    if ext in GBW_EXTS:
        return "gbw"
    if is_molden(path):
        return "molden"
    if ext in DENSITY_EXTS:
        return "density"
    return None


def base_name(path):
    """Strip the compound .molden.input suffix as well as ordinary ones."""
    name = os.path.basename(path)
    low = name.lower()
    if low.endswith(".molden.input"):
        return name[: -len(".molden.input")]
    return os.path.splitext(name)[0]


def scan_sources(roots):
    """
    Find every convertible file under the given directories.

    Returns a list of dicts with the path, kind, base name, and which
    products can be produced from it.
    """
    found = []
    seen = set()
    for root in roots or []:
        for folder, dirs, files in os.walk(root):
            dirs.sort()
            for f in sorted(files):
                path = os.path.join(folder, f)
                if path in seen:
                    continue
                kind = classify(path)
                if kind is None:
                    continue
                seen.add(path)
                stem = base_name(path)
                existing = _existing_cubes(folder, stem)
                found.append({
                    "path": path,
                    "folder": folder,
                    "kind": kind,
                    "base": stem,
                    "size": os.path.getsize(path),
                    "cubes": existing,
                })
    return found


def _existing_cubes(folder, stem):
    """Cubes already sitting next to a source, so work isn't repeated blindly."""
    out = []
    try:
        for f in os.listdir(folder):
            if f.lower().endswith(".cube") and f.startswith(stem):
                out.append(f)
    except OSError:
        pass
    return sorted(out)


def products_for(kind):
    """Human-readable list of what a source can yield."""
    if kind == "gbw":
        return ["molden", "HOMO/LUMO orbitals", "spin density"]
    if kind == "molden":
        return ["HOMO/LUMO orbitals"]
    if kind == "density":
        return ["density cube"]
    return []


# ─── Stage 1: gbw -> molden ───────────────────────────────────────────────────
def gbw_to_molden(gbw_path, log=None):
    """
    Run orca_2mkl. Returns the molden path.

    orca_2mkl takes the base name without extension and writes
    <base>.molden.input beside it.
    """
    folder = os.path.dirname(gbw_path)
    stem = base_name(gbw_path)
    exe = _which(ORCA_2MKL)
    if exe is None:
        raise RuntimeError("orca_2mkl is not on PATH")

    cmd = [exe, stem, "-molden"]
    if log:
        log(f"  {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=folder or ".", capture_output=True,
                          text=True)
    out = os.path.join(folder, stem + ".molden.input")
    if proc.returncode != 0 or not os.path.exists(out):
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise RuntimeError("orca_2mkl failed: " +
                           (detail[-1] if detail else
                            f"exit code {proc.returncode}"))
    return out


# ─── Stage 2: molden -> orbital cubes ─────────────────────────────────────────
def find_frontier(mo_occ):
    """
    HOMO and LUMO indices per spin channel.

    Returns [(label, spin_index, homo, lumo)] — one entry for a restricted
    calculation, two for unrestricted.
    """
    import numpy as np

    occ = np.asarray(mo_occ)
    if occ.ndim == 2:                       # unrestricted: shape (2, n_mo)
        result = []
        for spin, label in ((0, "ALPHA"), (1, "BETA")):
            o = occ[spin]
            result.append((label, spin) + _frontier(o))
        return result
    return [("", None) + _frontier(occ)]


def _frontier(o):
    import numpy as np

    occupied = np.where(o > 0)[0]
    if occupied.size == 0:
        return (None, 0)
    homo = int(occupied.max())
    empty = np.where(o == 0)[0]
    empty = empty[empty > homo]
    lumo = int(empty.min()) if empty.size else None
    return (homo, lumo)


def molden_to_cubes(molden_path, out_dir=None, grid=80, want_homo=True,
                    want_lumo=True, log=None, should_stop=None):
    """
    Write HOMO and/or LUMO cubes from a molden file.

    grid is the number of points per axis; cost scales with its cube, so 300
    (as in the original script) is 50x the work of 80 and can take minutes per
    orbital on a large basis.
    """
    from pyscf.tools import molden, cubegen

    out_dir = out_dir or os.path.dirname(molden_path)
    stem = base_name(molden_path)
    mol, _energy, mo_coeff, mo_occ, _irrep, _spins = molden.load(molden_path)

    written = []
    for label, spin, homo, lumo in find_frontier(mo_occ):
        coeff = mo_coeff[spin] if spin is not None else mo_coeff
        targets = []
        if want_homo and homo is not None:
            targets.append(("HOMO", homo))
        if want_lumo and lumo is not None:
            targets.append(("LUMO", lumo))
        for name, idx in targets:
            if should_stop and should_stop():
                return written
            suffix = f"{name}_{label}" if label else name
            out = os.path.join(out_dir, f"{stem}_{suffix}.cube")
            if log:
                log(f"  {os.path.basename(out)}  (MO {idx}, {grid}^3)")
            cubegen.orbital(mol, out, coeff[:, idx],
                            nx=grid, ny=grid, nz=grid)
            written.append(out)
    return written


# ─── Stage 3: gbw -> density cube via orca_plot ───────────────────────────────
# orca_plot is menu-driven. These are the keystrokes the original PLOT.txt
# supplied, with the grid size made configurable:
#   1, 3   choose plot type = spin density   (2 = electron density)
#   y      confirm
#   4, N   set the number of grid points
#   11     generate the plot
#   12     exit
PLOT_SPIN = 3
PLOT_DENSITY = 2


def density_cube(gbw_path, grid=300, kind="spin", log=None):
    """Drive orca_plot to write a spin- or electron-density cube."""
    exe = _which(ORCA_PLOT)
    if exe is None:
        raise RuntimeError("orca_plot is not on PATH")

    folder = os.path.dirname(gbw_path) or "."
    name = os.path.basename(gbw_path)
    plot_type = PLOT_SPIN if kind == "spin" else PLOT_DENSITY
    script = f"1\n{plot_type}\ny\n4\n{grid}\n11\n12\n"

    if log:
        log(f"  orca_plot {name} -i  ({kind} density, {grid} points)")
    proc = subprocess.run([exe, name, "-i"], cwd=folder, input=script,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise RuntimeError("orca_plot failed: " +
                           (detail[-1] if detail else
                            f"exit code {proc.returncode}"))
    # orca_plot names its output after the gbw base with its own suffix
    stem = base_name(gbw_path)
    produced = [os.path.join(folder, f) for f in os.listdir(folder)
                if f.startswith(stem) and f.lower().endswith(".cube")]
    return sorted(produced)


# ─── Batch driver ─────────────────────────────────────────────────────────────
def run_jobs(jobs, grid=80, density_grid=300, want_homo=True, want_lumo=True,
             want_density=False, log=None, progress=None, should_stop=None):
    """
    Execute a list of scan_sources() entries.

    Returns (written_paths, errors). One failure does not abort the batch —
    a bad file in the middle of a long run should not cost the whole run.
    """
    log = log or (lambda _m: None)
    written, errors = [], []
    total = max(1, len(jobs))

    for i, job in enumerate(jobs):
        if should_stop and should_stop():
            log("Cancelled.")
            break
        if progress:
            progress(i / total, os.path.basename(job["path"]))
        log(f"{os.path.basename(job['path'])}")

        try:
            molden_path = None
            if job["kind"] == "gbw":
                molden_path = gbw_to_molden(job["path"], log=log)
                written.append(molden_path)
            elif job["kind"] == "molden":
                molden_path = job["path"]

            if molden_path and (want_homo or want_lumo):
                written += molden_to_cubes(
                    molden_path, grid=grid, want_homo=want_homo,
                    want_lumo=want_lumo, log=log, should_stop=should_stop)

            if want_density and job["kind"] in ("gbw", "density"):
                gbw = job["path"]
                if job["kind"] == "density":
                    candidate = os.path.join(job["folder"], job["base"] + ".gbw")
                    gbw = candidate if os.path.exists(candidate) else None
                if gbw:
                    written += density_cube(gbw, grid=density_grid, log=log)
                else:
                    errors.append(f"{job['base']}: no matching .gbw for density")
        except Exception as exc:
            errors.append(f"{os.path.basename(job['path'])}: {exc}")
            log(f"  ERROR {exc}")

    if progress:
        progress(1.0, "done")
    return written, errors
