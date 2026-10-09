"""Convert a Gmsh surface to VTK for WingCAD, without opening either GUI."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from core.flowpanel_workflow import read_case, is_weber_case

if __name__ == "__main__":
    folder = Path(sys.argv[1]).resolve()
    if is_weber_case(read_case(folder)):
        import numpy as np
        from analysis.flowpanel.sweptwing.reconstruct_pressure import save_vtk
        nodes=np.loadtxt(folder/'nodes_C.csv',delimiter=',')
        cells=np.loadtxt(folder/'cells_C.csv',delimiter=',',dtype=int)-1
        assert nodes.ndim==2 and nodes.shape[1]==3 and cells.ndim==2 and cells.shape[1]==3
        assert np.isfinite(nodes).all() and cells.min()>=0 and cells.max()<len(nodes)
        save_vtk(folder/'surface.vtk',nodes,cells,{})
        sys.exit(0)
    import gmsh
    gmsh.initialize(["wingcad-mesh-preview"], readConfigFiles=False)
    try:
        gmsh.open(str(folder / "surface.msh"))
        gmsh.write(str(folder / "surface.vtk"))
    finally:
        gmsh.finalize()
