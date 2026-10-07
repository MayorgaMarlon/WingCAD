"""Build the Weber wing through WingCAD/OpenCascade, then mesh its STEP."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from analysis.flowpanel.prepare import mesh_level, LEVELS
from app.application import AeroApplication
from core.exporter import exportar_step


def main():
    import gmsh
    source = ROOT / "examples/08_weber_swept_wing.wingcad"
    output = ROOT / "exports/flowpanel/weber/wingcad"
    if output.exists():
        raise FileExistsError("Use a new output folder; existing benchmark cases are preserved.")
    output.mkdir(parents=True)
    app = AeroApplication()
    app.abrir_proyecto(source)
    wing = json.loads(source.read_text())["documento"]["objetos"][0]
    step = output / "analysis.step"
    exportar_step(app.documento.objetos[0].shape, step)
    LEVELS["benchmark"] = (0.12, 0.025)
    gmsh.initialize(["weber-wingcad"], readConfigFiles=False)
    try:
        mesh_level(gmsh, step, wing, "benchmark", output, hashlib.sha256(source.read_bytes()).hexdigest())
        gmsh.write(str(output / "mesh_preview.vtk"))
    finally:
        gmsh.finalize()
    import tomllib
    config = tomllib.loads((output / "case.toml").read_text())
    config.update(speed_mps=30.0, aoa_deg=4.2, moment_reference_m=[0.12446,0.,0.],
                  geometry="Weber RAE101 45deg", mesh_size_max_m=.12, mesh_size_min_m=.025)
    (output / "case.toml").write_text("".join(f"{k} = {json.dumps(v)}\n" for k,v in config.items()))


if __name__ == "__main__":
    main()
