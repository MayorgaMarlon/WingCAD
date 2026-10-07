"""Derive an open-tip surface from WingCAD's mesh to match the tutorial."""
import json
import shutil
import tomllib
from pathlib import Path
import gmsh
import numpy as np

ROOT = Path(__file__).resolve().parents[3]


def main():
    source = ROOT / "exports/flowpanel/weber/wingcad"
    output = source.with_name("wingcad_open_tips")
    if output.exists():
        raise FileExistsError(output)
    output.mkdir()
    gmsh.initialize(["match-reference-tips"], readConfigFiles=False)
    try:
        gmsh.open(str(source / "surface.msh"))
        keep, removed = [], []
        for dim,tag in gmsh.model.getEntities(2):
            _,coords,_ = gmsh.model.mesh.getNodes(dim,tag,includeBoundary=True)
            xyz = np.asarray(coords).reshape(-1,3)
            if len(xyz) and np.max(np.abs(np.abs(xyz[:,1])-1.2446)) < 1e-7:
                removed.append(tag)
            else:
                keep.append(tag)
        assert len(removed)==2, f"Expected exactly two tip caps: {removed}"
        gmsh.model.removePhysicalGroups()
        gmsh.model.addPhysicalGroup(2,keep)
        gmsh.option.setNumber("Mesh.SaveAll",0)
        gmsh.option.setNumber("Mesh.MshFileVersion",4.1)
        gmsh.option.setNumber("Mesh.Binary",0)
        gmsh.write(str(output / "surface.msh"))
        count = sum(len(gmsh.model.mesh.getElements(2,t)[1][0]) for t in keep)
    finally:
        gmsh.finalize()
    for name in ("te_left.msh","te_right.msh"):
        shutil.copyfile(source/name,output/name)
    config=tomllib.loads((source/'case.toml').read_text())
    config.update(panels=count, tip_caps=False, solver_formulation="direct_open_surface",
                  parent_closed_volume_m3=config.pop('signed_volume_m3'), normal_sign=1)
    (output/'case.toml').write_text(''.join(f'{k} = {json.dumps(v)}\n' for k,v in config.items()))
    print('Open-tip WingCAD mesh:',count,'panels')


if __name__ == '__main__':
    main()
