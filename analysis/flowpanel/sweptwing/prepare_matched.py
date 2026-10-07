"""Sample the WingCAD BRep at the tutorial's structured mesh stations, headless."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.gp import gp_Pnt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from app.application import AeroApplication
from core.exporter import exportar_step
from core.reference_airfoil import reference_contour, spacing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'exports/flowpanel/weber/matched_geometry')
    args = parser.parse_args()
    source = ROOT/'examples/09_weber_matched_reference.wingcad'
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f'Existing case preserved: {output}')
    app = AeroApplication()
    app.abrir_proyecto(source)
    shape = app.documento.objetos[0].shape
    assert BRepCheck_Analyzer(shape).IsValid(), 'Invalid WingCAD BRep'
    output.mkdir(parents=True)
    exportar_step(shape, output/'analysis.step')
    contour = reference_contour()*497.84
    stations = 1244.6-spacing(1244.6, 15, 10)
    max_projection = 0.
    for name, sign in [('L', -1), ('R', 1)]:
        nodes = []
        for y in stations:
            for x, z in contour:
                target = gp_Pnt(float(x+y), float(sign*y), float(z))
                distance = BRepExtrema_DistShapeShape(
                    BRepBuilderAPI_MakeVertex(target).Vertex(), shape)
                distance.Perform()
                assert distance.IsDone() and distance.NbSolution() > 0
                assert distance.Value() < 1e-5, f'Node off CAD by {distance.Value()} mm'
                point = distance.PointOnShape2(1)
                max_projection = max(max_projection, target.Distance(point))
                nodes.append([point.X()/1000, point.Y()/1000, point.Z()/1000])
        np.savetxt(output/f'nodes_{name}.csv', nodes, delimiter=',', fmt='%.17g')
    audit = dict(source=str(source.relative_to(ROOT)),
                 source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                 airfoil_sha256=hashlib.sha256((ROOT/'data/airfoils/rae101.csv').read_bytes()).hexdigest(),
                 brep_valid=True, nodes_per_half=768, expected_panels=2880,
                 maximum_projection_mm=max_projection,
                 method='Independent FITPACK sampling projected onto WingCAD OpenCascade BRep',
                 tip_caps_in_solver=False, units='m', speed_mps=30., aoa_deg=4.2,
                 density_kg_m3=1.225, bref_m=2.4892, sref_m2=2.4892*.49784)
    (output/'geometry_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
