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
    for symbol in (
        "gridgen_setverbose",
        "gridgen_printversion",
        "gridgen_printhelpalg",
        "gridgen_printhelpprm",
        "gridgen_generategrid",
        "gridgen_generategrid2",
    ):
        getattr(library, symbol)
    library.gridgen_setverbose.argtypes = [ctypes.c_int]
    library.gridgen_setverbose.restype = None
    library.gridgen_setverbose(0)

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
