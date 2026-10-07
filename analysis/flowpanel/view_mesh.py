"""Convert a Gmsh surface to VTK for WingCAD, without opening either GUI."""
import sys
from pathlib import Path
import gmsh

if __name__ == "__main__":
    folder = Path(sys.argv[1]).resolve()
    gmsh.initialize(["wingcad-mesh-preview"], readConfigFiles=False)
    try:
        gmsh.open(str(folder / "surface.msh"))
        gmsh.write(str(folder / "surface.vtk"))
    finally:
        gmsh.finalize()
