import ctypes
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile


bindir = Path(sys.prefix) / "Library" / "bin"
with os.add_dll_directory(str(bindir)):
    library = ctypes.CDLL(str(bindir / "gridgen.dll"))
    # Keep in sync with the gridgen.def exports in CMakeLists.txt
    for symbol in (
        "gridgen_setverbose",
        "gridgen_printversion",
        "gridgen_printhelpalg",
        "gridgen_printhelpprm",
        "gridgen_generategrid",
        "gridgen_generategrid2",
        # gridutils API that pygridgen calls through gridgen's library
        "gridnodes_getx",
        "gridnodes_gety",
        "gridnodes_getnce1",
        "gridnodes_getnce2",
        "gridnodes_destroy",
        "gridmap_build",
    ):
        getattr(library, symbol)
    library.gridgen_setverbose.argtypes = [ctypes.c_int]
    library.gridgen_setverbose.restype = None
    library.gridgen_setverbose(0)

# Generate a grid through the library API, as pygridgen does.
c_double_p = ctypes.POINTER(ctypes.c_double)
c_int_p = ctypes.POINTER(ctypes.c_int)
c_double_pp = ctypes.POINTER(c_double_p)
# cf. the gridgen_generategrid2 prototype in gridgen.h
library.gridgen_generategrid2.argtypes = (
    [ctypes.c_int]  # nbdry
    + [c_double_p] * 3  # xbdry, ybdry, beta
    + [ctypes.c_int] * 4  # ul, nx, ny, ngrid
    + [c_double_p] * 2  # xgrid, ygrid
    + [ctypes.c_int] * 2  # nnodes, newton
    + [ctypes.c_double]  # precision
    + [ctypes.c_int] * 4  # checksimplepoly, thin, nppe, verbose
    + [c_int_p, c_double_pp]  # nsigmas, sigmas
    + [c_int_p, c_double_pp, c_double_pp]  # nrect, xrect, yrect
)
library.gridgen_generategrid2.restype = ctypes.c_void_p
library.gridnodes_getx.restype = ctypes.POINTER(c_double_p)
library.gridnodes_gety.restype = ctypes.POINTER(c_double_p)
for function in (
    library.gridnodes_getx,
    library.gridnodes_gety,
    library.gridnodes_destroy,
):
    function.argtypes = [ctypes.c_void_p]
library.gridnodes_destroy.restype = None

boundary = [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)]
nbdry = len(boundary)
nx, ny = 41, 21
DoubleArray = ctypes.c_double * nbdry
nsigmas = ctypes.c_int(0)
sigmas = c_double_p()
nrect = ctypes.c_int(0)
xrect = c_double_p()
yrect = c_double_p()
nodes = library.gridgen_generategrid2(
    nbdry,
    DoubleArray(*(x for x, _ in boundary)),
    DoubleArray(*(y for _, y in boundary)),
    DoubleArray(*([1.0] * nbdry)),  # beta: four 90 degree corners
    0,  # ul: index of the upper-left corner
    nx,
    ny,
    0,  # ngrid: no focusing
    None,
    None,
    14,  # nnodes
    1,  # newton
    1e-12,  # precision
    1,  # checksimplepoly
    1,  # thin
    3,  # nppe
    0,  # verbose
    ctypes.byref(nsigmas),
    ctypes.byref(sigmas),
    ctypes.byref(nrect),
    ctypes.byref(xrect),
    ctypes.byref(yrect),
)
assert nodes, "gridgen_generategrid2 returned NULL"
# gridnodes stores the nodes contiguously, row after row
xs = library.gridnodes_getx(nodes)[0]
ys = library.gridnodes_gety(nodes)[0]
points = [(xs[i], ys[i]) for i in range(nx * ny)]
assert all(math.isfinite(x) and math.isfinite(y) for x, y in points)
assert all(-1e-9 <= x <= 2.0 + 1e-9 and -1e-9 <= y <= 1.0 + 1e-9 for x, y in points)
corners = [points[i] for i in (0, nx - 1, (ny - 1) * nx, nx * ny - 1)]
for x_expected, y_expected in boundary:
    assert any(
        math.isclose(x, x_expected, abs_tol=1e-6)
        and math.isclose(y, y_expected, abs_tol=1e-6)
        for x, y in corners
    ), corners
library.gridnodes_destroy(nodes)

# Exercise Triangle and complex arithmetic with a small rectangular grid.
with tempfile.TemporaryDirectory() as directory:
    work = Path(directory)
    (work / "boundary.txt").write_text(
        "0 0 1\n1 0 1\n1 1 1\n0 1 1\n", encoding="ascii"
    )
    (work / "grid.prm").write_text(
        "input boundary.txt\noutput grid.txt\nnx 5\nny 5\n", encoding="ascii"
    )
    subprocess.run(
        [str(bindir / "gridgen.exe"), "grid.prm"],
        cwd=work,
        check=True,
        timeout=60,
    )
    lines = (work / "grid.txt").read_text().splitlines()
    coordinates = [line.split() for line in lines if not line.startswith("##")]
    assert len(coordinates) == 25, lines
    assert all(
        len(point) == 2 and all(math.isfinite(float(value)) for value in point)
        for point in coordinates
    ), lines
