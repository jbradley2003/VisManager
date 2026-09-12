"""
Interactive Gaussian cube viewer for VisManager.

Optional module. VisManager imports it inside a try/except and simply drops
cube support if VTK is missing, so the base app keeps working (and keeps its
modest download size) for anyone who doesn't need this.

    pip install vtk

Design notes
------------
Rendering is done OFF SCREEN and handed back as a PIL image, which the main
window then draws on the canvas it already has. That was a deliberate choice
over embedding a native 3D widget:

  * VTK does ship a real Tk widget (vtkTkRenderWindowInteractor), but the
    PyPI wheels omit libvtkRenderingTk.so, so it cannot be loaded from a pip
    install. It needs a custom VTK build.
  * Going through the existing canvas means zoom, pan, Keep/Delete, flags,
    notes and PDF export all work on cube files with no special-casing.

Export covers both raster and vector. Vector output goes through GL2PS;
vtkSVGExporter exists in the wheel but produces an essentially empty file for
3D geometry, so it is not used.
"""

import os

try:
    import vtk
    from vtk.util import numpy_support
    VTK_AVAILABLE = True
    VTK_VERSION = vtk.vtkVersion.GetVTKVersion()
except Exception:                      # pragma: no cover - depends on install
    vtk = None
    VTK_AVAILABLE = False
    VTK_VERSION = None

from PIL import Image


BOHR_TO_ANGSTROM = 0.529177210903


def parse_cube(path):
    """
    Read a Gaussian cube file into (atoms, origin, spacing, values).

    Written by hand rather than using vtkGaussianCubeReader2, which mishandles
    this format in two ways that matter here:

      * it ignores the units flag (a negative atom count means the file is in
        Angstrom, positive means Bohr), and
      * it scales atom coordinates by the voxel size, so a 1.43 A bond can come
        back as anything depending on the grid resolution.

    The result is atoms that don't line up with the isosurface and bond
    perception that never fires, because every interatomic distance is wrong.

    Everything returned here is in Angstrom.

    atoms   : list of (atomic_number, x, y, z)
    origin  : (x, y, z) of voxel (0,0,0)
    spacing : (dx, dy, dz) voxel size along each axis
    values  : numpy array shaped (nx, ny, nz)
    """
    import numpy as np

    with open(path, "r", errors="replace") as f:
        f.readline()                      # two comment lines
        f.readline()

        parts = f.readline().split()
        n_atoms = int(parts[0])
        origin = [float(x) for x in parts[1:4]]

        # A negative atom count flags Angstrom input and also means an extra
        # line of orbital indices follows the atom block.
        angstrom_input = n_atoms < 0
        n_atoms = abs(n_atoms)

        dims, axes = [], []
        for _ in range(3):
            row = f.readline().split()
            count = int(row[0])
            # Per the spec a negative voxel count also signals Angstrom.
            if count < 0:
                angstrom_input = True
                count = abs(count)
            dims.append(count)
            axes.append([float(x) for x in row[1:4]])

        atoms = []
        for _ in range(n_atoms):
            row = f.readline().split()
            atoms.append((int(row[0]), float(row[2]), float(row[3]),
                          float(row[4])))

        if int(parts[0]) < 0:
            f.readline()                  # orbital index line

        raw = np.fromstring(f.read(), sep=" ") if hasattr(np, "fromstring") \
            else np.array(f.read().split(), dtype=float)

    scale = 1.0 if angstrom_input else BOHR_TO_ANGSTROM
    origin = [o * scale for o in origin]
    atoms = [(z, x * scale, y * scale, zz * scale) for z, x, y, zz in atoms]

    # Cube axes may be non-orthogonal in principle; in practice they are
    # axis-aligned, and vtkImageData can only represent that case anyway.
    spacing = [
        (axes[i][0] ** 2 + axes[i][1] ** 2 + axes[i][2] ** 2) ** 0.5 * scale
        for i in range(3)
    ]

    want = dims[0] * dims[1] * dims[2]
    raw = raw[:want]
    if raw.size < want:                    # truncated file
        raw = np.pad(raw, (0, want - raw.size))
    # Cube data runs with the LAST axis varying fastest.
    values = raw.reshape(dims[0], dims[1], dims[2])
    return atoms, tuple(origin), tuple(spacing), values


def choose_isovalue(values, volume_fraction=0.12):
    """
    Pick a starting isovalue that actually shows something.

    A fixed fraction of the peak is a poor default: spin-density and HFC cubes
    have sharp nuclear cusps, so the maximum is orders of magnitude above the
    values that describe the feature of interest, and any fraction of it
    renders as a speck at one nucleus. Choosing the level that encloses a small
    share of the grid volume adapts to whatever the data looks like.
    """
    import numpy as np

    mag = np.abs(values).ravel()
    mag = mag[mag > 0]
    if mag.size == 0:
        return 0.0
    q = float(np.quantile(mag, 1.0 - volume_fraction))
    peak = float(mag.max())
    # Guard rails only: the quantile normally decides. Capping near the peak
    # would reproduce the very problem this replaces — a speck at one nucleus.
    return max(min(q, peak * 0.5), peak * 1e-4)


CUBE_EXTS = {".cube", ".cub"}

# Export targets. "vector" entries keep curves as geometry and stay sharp at
# any size; "raster" entries honour the resolution multiplier.
EXPORT_FORMATS = [
    ("png",  "PNG",              "raster"),
    ("tiff", "TIFF",             "raster"),
    ("jpeg", "JPEG",             "raster"),
    ("svg",  "SVG (vector)",     "vector"),
    ("pdf",  "PDF (vector)",     "vector"),
    ("eps",  "EPS (vector)",     "vector"),
]
FORMAT_KIND = {k: kind for k, _label, kind in EXPORT_FORMATS}
FORMAT_LABEL = {k: label for k, label, _kind in EXPORT_FORMATS}

# Multipliers applied to the on-screen size for raster export.
SCALE_CHOICES = [1, 2, 3, 4, 6, 8]

DEFAULT_POS_COLOR = (0.95, 0.82, 0.25)
DEFAULT_NEG_COLOR = (0.25, 0.73, 0.85)


class CubeScene:
    """
    One loaded cube file plus its camera state.

    Isosurfaces are rebuilt only when the isovalue changes; camera moves reuse
    the existing geometry, which is what keeps dragging responsive.
    """

    def __init__(self, path, bg=(0.043, 0.043, 0.078)):
        if not VTK_AVAILABLE:
            raise RuntimeError("VTK is not installed")

        self.path = path
        self.error = ""
        self._bg = bg

        self.isovalue = 0.02
        self.opacity = 0.65
        self.show_atoms = True
        self.show_box = False
        self.smooth = True
        self.pos_color = DEFAULT_POS_COLOR
        self.neg_color = DEFAULT_NEG_COLOR

        self._surf_actors = []
        self.n_bonds = 0
        self._mol_actor = None
        self._box_actor = None
        self._size = (0, 0)

        import numpy as np

        atoms, origin, spacing, values = parse_cube(path)
        if values.size == 0:
            raise ValueError("No volumetric data found in this cube file")

        self.atoms = atoms
        self.n_atoms = len(atoms)
        self.dimensions = tuple(values.shape)
        self.data_range = (float(values.min()), float(values.max()))

        # Build the volume ourselves so grid and atoms share one coordinate
        # system, both in Angstrom.
        img = vtk.vtkImageData()
        img.SetDimensions(*values.shape)
        img.SetOrigin(*origin)
        img.SetSpacing(*spacing)
        flat = np.ascontiguousarray(values.transpose(2, 1, 0).ravel())
        arr = numpy_support.numpy_to_vtk(flat, deep=True,
                                         array_type=vtk.VTK_DOUBLE)
        arr.SetName("cube")
        img.GetPointData().SetScalars(arr)
        self.grid = img

        self.molecule = vtk.vtkMolecule()
        for z, x, y, zz in atoms:
            self.molecule.AppendAtom(z, x, y, zz)

        peak = max(abs(self.data_range[0]), abs(self.data_range[1]))
        self.max_iso = peak
        self.isovalue = choose_isovalue(values) or (peak * 0.08 if peak else 0.02)

        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(*self._bg)
        self.render_window = vtk.vtkRenderWindow()
        self.render_window.SetOffScreenRendering(1)
        self.render_window.AddRenderer(self.renderer)
        self.render_window.SetMultiSamples(0)      # GL2PS needs this off

        self._build_molecule()
        self._build_box()
        self.rebuild_surfaces()
        self.reset_camera()

    # ── Geometry ─────────────────────────────────────────────────────────────
    def rebuild_surfaces(self):
        """Recompute the +/- isosurfaces. Called only when the value changes."""
        for a in self._surf_actors:
            self.renderer.RemoveActor(a)
        self._surf_actors = []

        v = abs(self.isovalue)
        if v <= 0:
            return

        for level, color in ((v, self.pos_color), (-v, self.neg_color)):
            mc = vtk.vtkMarchingCubes()
            mc.SetInputData(self.grid)
            mc.SetValue(0, level)
            mc.ComputeNormalsOn()
            src = mc

            if self.smooth:
                sm = vtk.vtkWindowedSincPolyDataFilter()
                sm.SetInputConnection(mc.GetOutputPort())
                sm.SetNumberOfIterations(15)
                sm.BoundarySmoothingOn()
                sm.NonManifoldSmoothingOn()
                sm.NormalizeCoordinatesOn()
                src = sm

            nrm = vtk.vtkPolyDataNormals()
            nrm.SetInputConnection(src.GetOutputPort())
            nrm.SetFeatureAngle(90.0)
            nrm.Update()

            if nrm.GetOutput().GetNumberOfPolys() == 0:
                continue               # isovalue above the data's peak

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(nrm.GetOutputPort())
            mapper.ScalarVisibilityOff()

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            p = actor.GetProperty()
            p.SetColor(*color)
            p.SetOpacity(self.opacity)
            p.SetSpecular(0.3)
            p.SetSpecularPower(30)
            self.renderer.AddActor(actor)
            self._surf_actors.append(actor)

    def _build_molecule(self):
        if not self.molecule or self.n_atoms == 0:
            return
        mol = self.molecule
        # Cube files carry atoms but no connectivity, so bonds are inferred
        # from covalent radii.
        try:
            perceiver = vtk.vtkSimpleBondPerceiver()
            perceiver.SetInputData(mol)
            perceiver.SetTolerance(0.45)
            perceiver.Update()
            if perceiver.GetOutput().GetNumberOfBonds() > 0:
                mol = perceiver.GetOutput()
                self.n_bonds = mol.GetNumberOfBonds()
        except Exception:
            pass

        mapper = vtk.vtkMoleculeMapper()
        mapper.SetInputData(mol)
        try:
            mapper.UseBallAndStickSettings()
            # Calibrated against correctly-scaled Angstrom coordinates. The
            # earlier larger values were compensating for atoms that VTK's
            # reader had mis-scaled; with real distances they simply swallow
            # the isosurface.
            mapper.SetAtomicRadiusScaleFactor(0.24)
            mapper.SetBondRadius(0.11)
        except Exception:
            pass
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        self._mol_actor = actor
        if self.show_atoms:
            self.renderer.AddActor(actor)

    def _build_box(self):
        outline = vtk.vtkOutlineFilter()
        outline.SetInputData(self.grid)
        outline.Update()
        m = vtk.vtkPolyDataMapper()
        m.SetInputConnection(outline.GetOutputPort())
        a = vtk.vtkActor()
        a.SetMapper(m)
        a.GetProperty().SetColor(0.35, 0.35, 0.45)
        a.GetProperty().SetLineWidth(1)
        self._box_actor = a

    # ── Settings ─────────────────────────────────────────────────────────────
    def set_isovalue(self, value):
        self.isovalue = max(0.0, float(value))
        self.rebuild_surfaces()

    def set_opacity(self, value):
        self.opacity = max(0.05, min(1.0, float(value)))
        for a in self._surf_actors:
            a.GetProperty().SetOpacity(self.opacity)

    def set_show_atoms(self, on):
        self.show_atoms = bool(on)
        if self._mol_actor is None:
            return
        if on:
            self.renderer.AddActor(self._mol_actor)
        else:
            self.renderer.RemoveActor(self._mol_actor)

    def set_show_box(self, on):
        self.show_box = bool(on)
        if self._box_actor is None:
            return
        if on:
            self.renderer.AddActor(self._box_actor)
        else:
            self.renderer.RemoveActor(self._box_actor)

    def set_smooth(self, on):
        self.smooth = bool(on)
        self.rebuild_surfaces()

    # ── Camera ───────────────────────────────────────────────────────────────
    def reset_camera(self):
        self.renderer.ResetCamera()
        cam = self.renderer.GetActiveCamera()
        cam.Elevation(18)
        cam.Azimuth(24)
        cam.OrthogonalizeViewUp()
        self.renderer.ResetCameraClippingRange()

    def rotate(self, dx, dy):
        cam = self.renderer.GetActiveCamera()
        cam.Azimuth(-dx * 0.4)
        cam.Elevation(dy * 0.4)
        cam.OrthogonalizeViewUp()
        self.renderer.ResetCameraClippingRange()

    def zoom(self, factor):
        cam = self.renderer.GetActiveCamera()
        if cam.GetParallelProjection():
            cam.SetParallelScale(cam.GetParallelScale() / factor)
        else:
            cam.Dolly(factor)
        self.renderer.ResetCameraClippingRange()

    def roll(self, degrees):
        self.renderer.GetActiveCamera().Roll(degrees)

    # ── Rendering ────────────────────────────────────────────────────────────
    def render(self, width, height):
        """Render offscreen and return a PIL image."""
        width = max(32, int(width))
        height = max(32, int(height))
        if (width, height) != self._size:
            self.render_window.SetSize(width, height)
            self._size = (width, height)
            self.renderer.ResetCameraClippingRange()

        self.render_window.Render()

        w2i = vtk.vtkWindowToImageFilter()
        w2i.SetInput(self.render_window)
        w2i.ReadFrontBufferOff()
        w2i.Update()

        img = w2i.GetOutput()
        dims = img.GetDimensions()
        arr = numpy_support.vtk_to_numpy(img.GetPointData().GetScalars())
        arr = arr.reshape(dims[1], dims[0], -1)[::-1]
        mode = "RGBA" if arr.shape[2] == 4 else "RGB"
        return Image.fromarray(arr, mode)

    # ── Export ───────────────────────────────────────────────────────────────
    def export(self, path, fmt="png", scale=2, transparent=False,
               white_background=False):
        """
        Write the current view to disk.

        fmt: png / tiff / jpeg / svg / pdf / eps
        scale: resolution multiplier, raster formats only. Vector output is
               resolution-independent, so the multiplier is ignored there.

        Returns a short description of what was written.
        """
        fmt = fmt.lower().lstrip(".")
        if fmt == "jpg":
            fmt = "jpeg"
        if fmt not in FORMAT_KIND:
            raise ValueError(f"Unsupported export format: {fmt}")

        old_bg = self.renderer.GetBackground()
        if white_background:
            self.renderer.SetBackground(1.0, 1.0, 1.0)
        try:
            if FORMAT_KIND[fmt] == "vector":
                return self._export_vector(path, fmt)
            return self._export_raster(path, fmt, scale, transparent)
        finally:
            self.renderer.SetBackground(*old_bg)

    def _export_raster(self, path, fmt, scale, transparent):
        scale = max(1, int(scale))
        self.render_window.Render()

        w2i = vtk.vtkWindowToImageFilter()
        w2i.SetInput(self.render_window)
        w2i.SetScale(scale)
        w2i.ReadFrontBufferOff()
        if transparent and fmt in ("png", "tiff"):
            w2i.SetInputBufferTypeToRGBA()
        w2i.Update()

        writer = {"png": vtk.vtkPNGWriter,
                  "tiff": vtk.vtkTIFFWriter,
                  "jpeg": vtk.vtkJPEGWriter}[fmt]()
        if fmt == "jpeg":
            writer.SetQuality(95)
        writer.SetFileName(path)
        writer.SetInputConnection(w2i.GetOutputPort())
        writer.Write()

        dims = w2i.GetOutput().GetDimensions()
        return f"{dims[0]} x {dims[1]} px"

    def _export_vector(self, path, fmt):
        # GL2PS writes <prefix>.<ext> itself, so hand it a prefix and move the
        # result to the exact filename the user chose.
        base, _ext = os.path.splitext(path)
        exporter = vtk.vtkGL2PSExporter()
        exporter.SetRenderWindow(self.render_window)
        exporter.SetFilePrefix(base)
        exporter.SetFileFormat({"svg": exporter.SVG_FILE,
                                "pdf": exporter.PDF_FILE,
                                "eps": exporter.EPS_FILE}[fmt])
        exporter.CompressOff()
        exporter.SetSortToBSP()          # correct depth order for transparency
        exporter.DrawBackgroundOn()
        exporter.Write3DPropsAsRasterImageOff()
        exporter.Write()

        produced = f"{base}.{fmt}"
        if produced != path and os.path.exists(produced):
            if os.path.exists(path):
                os.remove(path)
            os.replace(produced, path)
        if not os.path.exists(path):
            raise RuntimeError("The vector exporter produced no file")
        return f"vector, {os.path.getsize(path) / 1024:.0f} KB"

    def close(self):
        try:
            self.render_window.Finalize()
        except Exception:
            pass


def is_cube(path):
    return os.path.splitext(path)[1].lower() in CUBE_EXTS


def describe_backend():
    if not VTK_AVAILABLE:
        return "3D cube viewer unavailable — pip install vtk"
    return f"cube viewer via VTK {VTK_VERSION}"
