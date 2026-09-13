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

    # VTK pops up its own "vtkOutputWindow" for every warning. In a packaged
    # GUI app that is a stray window the user never asked for, so send the
    # messages to a buffer instead.
    try:
        _vtk_log = vtk.vtkStringOutputWindow()
        vtk.vtkOutputWindow.SetInstance(_vtk_log)
    except Exception:
        _vtk_log = None
except Exception:                      # pragma: no cover - depends on install
    vtk = None
    numpy_support = None
    VTK_AVAILABLE = False
    VTK_VERSION = None
    _vtk_log = None


# ─── OpenGL capability ────────────────────────────────────────────────────────
# VTK 9's rendering backend needs OpenGL 3.2 core. Some environments only
# offer 2.1 — notably Wine on macOS, whose WGL bridge exposes 2.1 by default.
# VTK does not fail gracefully there: it logs a warning and then crashes the
# process. Checking up front turns a hard crash into a readable message.
_GL_OK = None
_GL_MESSAGE = ""

GL_HELP = (
    "3D rendering needs OpenGL 3.2 or newer, and this system reports an "
    "older version.\n\n"
    "Running under Wine? Wine's OpenGL bridge defaults to 2.1. Placing "
    "Mesa's software opengl32.dll beside VisManager.exe gives it a modern "
    "software OpenGL and fixes this.\n\n"
    "Everything else in VisManager works normally; only .cube files need 3D."
)


def opengl_ok():
    """True when this machine can drive VTK's renderer. Result is cached."""
    global _GL_OK, _GL_MESSAGE
    if _GL_OK is not None:
        return _GL_OK
    if not VTK_AVAILABLE:
        _GL_OK, _GL_MESSAGE = False, "VTK is not installed"
        return _GL_OK
    try:
        rw = vtk.vtkRenderWindow()
        rw.SetOffScreenRendering(1)
        rw.SetSize(32, 32)
        supported = bool(rw.SupportsOpenGL())
        if supported:
            # SupportsOpenGL() alone is not conclusive on every driver, so
            # make it actually draw something before trusting it.
            ren = vtk.vtkRenderer()
            rw.AddRenderer(ren)
            rw.Render()
        try:
            rw.Finalize()
        except Exception:
            pass
        _GL_OK = supported
        _GL_MESSAGE = "" if supported else GL_HELP
    except Exception as exc:
        _GL_OK = False
        _GL_MESSAGE = f"{GL_HELP}\n\n({type(exc).__name__}: {exc})"
    return _GL_OK


def opengl_message():
    opengl_ok()
    return _GL_MESSAGE

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

# Rendering quality presets.
#
# Shadow maps are deliberately absent. vtkShadowMapPass drops translucent
# geometry entirely — isosurfaces simply disappear, leaving only the atoms —
# and on opaque surfaces it puts a hard self-shadowing band across smooth
# convex lobes. Both were measured; neither is acceptable for this content.
QUALITY_LEVELS = [
    ("fast",    "Fast",    "three-point lighting"),
    ("quality", "Quality", "+ correct transparency, antialiasing"),
    ("best",    "Best",    "+ ambient occlusion"),
]
QUALITY_LABEL = {k: label for k, label, _d in QUALITY_LEVELS}
QUALITY_NOTE = {k: note for k, _l, note in QUALITY_LEVELS}

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
        if not opengl_ok():
            raise RuntimeError(opengl_message())

        self.path = path
        self.error = ""
        self._bg = bg

        self.isovalue = 0.02
        self.opacity = 0.65
        self.show_atoms = True
        self.show_box = False
        self.smooth = True
        self.quality = "quality"
        self.use_shadows = False
        self.use_ssao = False
        self.use_fxaa = True
        self.use_ordering = True
        self.atom_scheme = "element"
        self.atom_overrides = {}        # {atomic_number: (r, g, b)}
        self._atom_lut = None
        self.ssao = False          # screen-space ambient occlusion
        self.shadows = False       # shadow mapping
        self.depth_peel = True     # order-correct transparency
        self.fxaa = True           # cheap edge anti-aliasing
        self.pos_color = DEFAULT_POS_COLOR
        self.neg_color = DEFAULT_NEG_COLOR

        self._surf_actors = []
        self._pass = None
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

        self._build_lights()
        self._build_molecule()
        self._build_box()
        self.rebuild_surfaces()
        self.apply_quality()
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
        self._set_shading(0.30 if self.use_shadows else 0.12)

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

    # ── Lighting and quality ─────────────────────────────────────────────────
    def _build_lights(self):
        """
        A three-point light rig.

        VTK's default single headlight casts no useful shadow, because it sits
        exactly at the camera — every shadow falls directly behind the object
        where it cannot be seen.
        """
        try:
            kit = vtk.vtkLightKit()
            kit.SetKeyLightWarmth(0.58)
            kit.SetFillLightWarmth(0.42)
            kit.SetKeyLightIntensity(1.1)
            kit.SetKeyLightElevation(40)
            kit.SetKeyLightAzimuth(-35)
            kit.AddLightsToRenderer(self.renderer)
            self._light_kit = kit
        except Exception:
            self._light_kit = None

    def set_ssao(self, on):
        self.ssao = bool(on)
        self.apply_quality()

    def set_shadows(self, on):
        self.shadows = bool(on)
        self.apply_quality()

    def set_depth_peel(self, on):
        self.depth_peel = bool(on)
        self.apply_quality()

    def set_fxaa(self, on):
        self.fxaa = bool(on)
        self.apply_quality()

    def apply_quality(self):
        """
        Rebuild the render-pass chain for the current toggles.

        The ordering matters. vtkShadowMapPass renders opaque geometry only,
        so used on its own it makes translucent isosurfaces disappear entirely
        — the translucent, volumetric and overlay passes have to be appended
        after it by hand. SSAO then wraps whatever that produces.
        """
        ren = self.renderer

        # Passes own GPU framebuffers. Dropping one without releasing its
        # resources leaks them and VTK complains loudly on the next swap.
        old = getattr(self, "_pass", None)
        if old is not None:
            try:
                old.ReleaseGraphicsResources(self.render_window)
            except Exception:
                pass
            self._pass = None

        try:
            ren.SetUseDepthPeeling(bool(self.depth_peel))
            ren.SetMaximumNumberOfPeels(6)
            ren.SetOcclusionRatio(0.05)
            ren.SetUseFXAA(bool(self.fxaa))
        except Exception:
            pass

        if not (self.ssao or self.shadows):
            try:
                ren.SetPass(None)
            except Exception:
                pass
            return

        try:
            if self.shadows:
                shadow = vtk.vtkShadowMapPass()
                passes = vtk.vtkRenderPassCollection()
                passes.AddItem(shadow.GetShadowMapBakerPass())
                passes.AddItem(shadow)
                # Without these three the surfaces vanish behind the shadows.
                passes.AddItem(vtk.vtkTranslucentPass())
                passes.AddItem(vtk.vtkVolumetricPass())
                passes.AddItem(vtk.vtkOverlayPass())
                seq = vtk.vtkSequencePass()
                seq.SetPasses(passes)
                chain = vtk.vtkCameraPass()
                chain.SetDelegatePass(seq)
            else:
                chain = vtk.vtkRenderStepsPass()

            if self.ssao:
                bounds = self.grid.GetBounds()
                diag = max(1e-6, (
                    (bounds[1] - bounds[0]) ** 2 +
                    (bounds[3] - bounds[2]) ** 2 +
                    (bounds[5] - bounds[4]) ** 2) ** 0.5)
                ao = vtk.vtkSSAOPass()
                ao.SetRadius(diag * 0.08)
                ao.SetBias(diag * 0.002)
                ao.SetKernelSize(64)
                ao.BlurOn()
                ao.SetDelegatePass(chain)
                chain = ao

            ren.SetPass(chain)
            self._pass = chain
        except Exception:
            # Any driver that can't manage the passes falls back to plain
            # rendering rather than losing the picture.
            try:
                ren.SetPass(None)
            except Exception:
                pass
            self.ssao = self.shadows = False

    # ── Rendering quality ────────────────────────────────────────────────────
    def set_effects(self, shadows=None, ssao=None, fxaa=None, ordering=None):
        """
        Toggle rendering effects individually.

        Shadows are offered because they were asked for, but they come with a
        real caveat: vtkShadowMapPass does not render translucent geometry, so
        an isosurface below full opacity disappears under it. The UI warns and
        the opacity is forced to 1.0 while shadows are on.
        """
        ren, rw = self.renderer, self.render_window
        if ordering is not None:
            self.use_ordering = bool(ordering)
        if ssao is not None:
            self.use_ssao = bool(ssao)
        if fxaa is not None:
            self.use_fxaa = bool(fxaa)
        if shadows is not None:
            self.use_shadows = bool(shadows)

        try:
            rw.SetAlphaBitPlanes(1 if self.use_ordering else 0)
            ren.SetUseDepthPeeling(self.use_ordering)
            if self.use_ordering:
                ren.SetMaximumNumberOfPeels(8)
                ren.SetOcclusionRatio(0.05)
        except Exception:
            pass
        try:
            ren.SetUseFXAA(self.use_fxaa)
        except Exception:
            pass
        try:
            ren.SetUseSSAO(self.use_ssao)
            if self.use_ssao:
                span = self._scene_span()
                ren.SetSSAORadius(span * 0.12)
                ren.SetSSAOBias(span * 0.001)
                ren.SetSSAOKernelSize(32)
                ren.SetSSAOBlur(True)
        except Exception:
            pass

        try:
            if self.use_shadows:
                self._setup_lights(for_shadows=True)
                baker = vtk.vtkShadowMapBakerPass()
                try:
                    # A low-resolution map is what produced the hard band
                    # across smooth lobes; VTK exposes no depth bias, so
                    # resolution is the only lever.
                    baker.SetResolution(2048)
                except Exception:
                    pass
                smp = vtk.vtkShadowMapPass()
                smp.SetShadowMapBakerPass(baker)
                seq = vtk.vtkSequencePass()
                col = vtk.vtkRenderPassCollection()
                col.AddItem(baker)
                col.AddItem(smp)
                seq.SetPasses(col)
                cam = vtk.vtkCameraPass()
                cam.SetDelegatePass(seq)
                ren.SetPass(cam)
                self._pass = cam
                # Unlit regions render pure black without an ambient term,
                # which looks like a rendering fault rather than a shadow.
                self._set_shading(ambient=0.30)
                self.set_opacity(1.0)      # translucency vanishes otherwise
            else:
                if self._pass is not None:
                    try:
                        self._pass.ReleaseGraphicsResources(rw)
                    except Exception:
                        pass
                ren.SetPass(None)
                self._pass = None
                self._setup_lights(for_shadows=False)
                self._set_shading(ambient=0.12)
        except Exception:
            pass

    def _set_shading(self, ambient):
        for actor in self._surf_actors + ([self._mol_actor]
                                          if self._mol_actor else []):
            pr = actor.GetProperty()
            pr.SetAmbient(ambient)
            pr.SetDiffuse(1.0 - ambient * 0.4)

    def set_colors(self, pos=None, neg=None, atoms_scheme=None):
        """Recolour the isosurfaces, and optionally the atoms."""
        if pos is not None:
            self.pos_color = tuple(pos)
        if neg is not None:
            self.neg_color = tuple(neg)
        for actor, colour in zip(self._surf_actors, (self.pos_color,
                                                     self.neg_color)):
            actor.GetProperty().SetColor(*colour)
        if atoms_scheme is not None:
            self.set_atom_scheme(atoms_scheme)

    ATOM_SCHEMES = ("element", "mono", "warm", "cool")
    SCHEME_COLORS = {"mono": (0.78, 0.78, 0.82),
                     "warm": (0.85, 0.62, 0.42),
                     "cool": (0.55, 0.72, 0.88)}

    def elements_present(self):
        """Atomic numbers in this file, in ascending order."""
        return sorted({z for z, _x, _y, _z in self.atoms})

    @staticmethod
    def element_symbol(z):
        try:
            return vtk.vtkPeriodicTable().GetSymbol(int(z))
        except Exception:
            return str(z)

    @staticmethod
    def element_default_color(z):
        try:
            return tuple(vtk.vtkPeriodicTable().GetDefaultRGBTuple(int(z)))
        except Exception:
            return (0.6, 0.6, 0.6)

    def set_atom_color(self, z, rgb):
        """Override one element's colour. rgb=None restores the default."""
        if rgb is None:
            self.atom_overrides.pop(int(z), None)
        else:
            self.atom_overrides[int(z)] = tuple(rgb)
        self._apply_atom_colors()

    def clear_atom_colors(self):
        self.atom_overrides = {}
        self._apply_atom_colors()

    def set_atom_scheme(self, scheme):
        self.atom_scheme = scheme if scheme in self.ATOM_SCHEMES else "element"
        self._apply_atom_colors()

    def _apply_atom_colors(self):
        """
        Colour atoms through a lookup table indexed by atomic number.

        The earlier approach set AtomColorMode(0) plus SetAtomColor, which had
        no visible effect — every scheme rendered identically. Supplying a LUT
        and leaving the mapper in per-atom mode does work, and it is also what
        makes per-element overrides possible at all.
        """
        if self._mol_actor is None:
            return
        mapper = self._mol_actor.GetMapper()
        flat = self.SCHEME_COLORS.get(self.atom_scheme)

        lut = vtk.vtkLookupTable()
        lut.SetNumberOfTableValues(119)
        lut.SetRange(0, 118)
        for z in range(119):
            if z in self.atom_overrides:
                rgb = self.atom_overrides[z]
            elif flat is not None:
                rgb = flat
            else:
                rgb = self.element_default_color(z)
            lut.SetTableValue(z, rgb[0], rgb[1], rgb[2], 1.0)
        lut.Build()

        try:
            mapper.SetAtomColorMode(1)        # per-atom, read from the LUT
            mapper.SetLookupTable(lut)
            mapper.SetBondColorMode(1)
        except Exception:
            pass
        self._mol_actor.GetProperty().SetColor(1.0, 1.0, 1.0)
        self._atom_lut = lut

    def set_background(self, rgb):
        self._bg = tuple(rgb)
        self.renderer.SetBackground(*self._bg)

    def set_quality(self, level):
        """Apply a rendering preset. Safe to call repeatedly."""
        if level not in QUALITY_LABEL:
            level = "quality"
        self.quality = level
        ren, rw = self.renderer, self.render_window

        self._setup_lights()

        self.use_ordering = level in ("quality", "best")
        self.use_ssao = level == "best"
        self.use_fxaa = level in ("quality", "best")
        want_peel, want_ssao, want_fxaa = (self.use_ordering, self.use_ssao,
                                           self.use_fxaa)

        try:
            # Depth peeling resolves the draw order of overlapping translucent
            # surfaces. Without it a +/- pair of lobes blends in whatever order
            # the triangles happen to arrive, which visibly changes as you
            # rotate.
            rw.SetAlphaBitPlanes(1 if want_peel else 0)
            ren.SetUseDepthPeeling(want_peel)
            if want_peel:
                ren.SetMaximumNumberOfPeels(8)
                ren.SetOcclusionRatio(0.05)
        except Exception:
            pass

        try:
            ren.SetUseFXAA(want_fxaa)
        except Exception:
            pass

        try:
            ren.SetUseSSAO(want_ssao)
            if want_ssao:
                span = self._scene_span()
                # The occlusion radius is a world-space distance, so it has to
                # track the size of the molecule rather than be a constant.
                ren.SetSSAORadius(span * 0.12)
                ren.SetSSAOBias(span * 0.001)
                ren.SetSSAOKernelSize(32)
                ren.SetSSAOBlur(True)
        except Exception:
            pass

    def _scene_span(self):
        b = self.grid.GetBounds()
        return max(b[1] - b[0], b[3] - b[2], b[5] - b[4]) or 1.0

    def _setup_lights(self, for_shadows=False):
        """
        Key / fill / rim rig.

        VTK's default is a single headlight, which flattens a rounded
        isosurface into a featureless disc — the shape reads only from its
        outline. Three lights restore the form, and measured slightly faster
        than the default besides.
        """
        ren = self.renderer
        ren.RemoveAllLights()
        b = self.grid.GetBounds()
        centre = ((b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2)
        span = self._scene_span()
        if for_shadows:
            # Shadow casting needs a positional light with a cone; a purely
            # directional key produces no usable shadow map here.
            key = vtk.vtkLight()
            key.SetLightTypeToSceneLight()
            key.SetPositional(True)
            key.SetConeAngle(45)
            key.SetPosition(centre[0] + span * 1.4, centre[1] + span * 1.5,
                            centre[2] + span * 1.7)
            key.SetFocalPoint(*centre)
            key.SetIntensity(1.0)
            ren.AddLight(key)
            rig = (((-1.0, 0.3, 0.6), 0.35), ((0.0, -1.0, -0.6), 0.25))
        else:
            rig = (((1.0, 1.0, 1.0), 1.00),      # key
                   ((-1.0, 0.4, 0.6), 0.45),     # fill
                   ((0.0, -1.0, -0.8), 0.30))    # rim

        for direction, intensity in rig:
            light = vtk.vtkLight()
            light.SetLightTypeToSceneLight()
            light.SetPosition(centre[0] + direction[0] * span * 2,
                              centre[1] + direction[1] * span * 2,
                              centre[2] + direction[2] * span * 2)
            light.SetFocalPoint(*centre)
            light.SetIntensity(intensity)
            light.SetPositional(False)
            ren.AddLight(light)

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
            if getattr(self, "_pass", None) is not None:
                self._pass.ReleaseGraphicsResources(self.render_window)
                self._pass = None
        except Exception:
            pass
        try:
            self.render_window.Finalize()
        except Exception:
            pass


def is_cube(path):
    return os.path.splitext(path)[1].lower() in CUBE_EXTS


def describe_backend():
    if not VTK_AVAILABLE:
        return "3D cube viewer unavailable — pip install vtk"
    if not opengl_ok():
        return "3D unavailable — OpenGL 3.2+ required"
    return f"cube viewer via VTK {VTK_VERSION}"
