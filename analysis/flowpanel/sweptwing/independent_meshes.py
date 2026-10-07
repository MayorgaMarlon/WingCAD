"""Independent WingCAD/Gmsh refinement study; no reference mesh is used."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tomllib

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from analysis.flowpanel.prepare import mesh_level, LEVELS
from app.application import AeroApplication
from core.exporter import exportar_step

SIZES = {'coarse': (.18, .0375), 'medium': (.12, .025), 'fine': (.08, .025/1.5)}


def remove_caps(gmsh, output):
    keep, caps, triangles = [], [], []
    for dim, tag in gmsh.model.getEntities(2):
        _, coords, _ = gmsh.model.mesh.getNodes(dim, tag, includeBoundary=True)
        xyz = np.asarray(coords).reshape(-1, 3)
        if len(xyz) and np.max(abs(abs(xyz[:, 1])-1.2446)) < 1e-7:
            caps.append(tag)
        else:
            keep.append(tag)
            types, _, connectivity = gmsh.model.mesh.getElements(2, tag)
            assert list(types) == [2], 'Expected linear triangles'
            triangles.extend(np.asarray(connectivity[0]).reshape(-1, 3))
    assert len(caps) == 2, f'Expected two tip caps, got {caps}'
    tags, coords, _ = gmsh.model.mesh.getNodes()
    points = dict(zip(map(int, tags), np.asarray(coords).reshape(-1, 3)))
    incidence, orientation = Counter(), Counter()
    for tri in triangles:
        for u, v in zip(tri, np.roll(tri, -1)):
            edge = tuple(sorted((int(u), int(v))))
            incidence[edge] += 1
            orientation[edge] += 1 if u < v else -1
    boundary = [e for e, count in incidence.items() if count == 1]
    assert boundary and all(v in (1, 2) for v in incidence.values())
    assert all(orientation[e] == 0 for e, count in incidence.items() if count == 2)
    assert all(abs(abs(points[a][1])-1.2446) < 1e-7 and
               abs(points[a][1]-points[b][1]) < 1e-7 for a, b in boundary), 'Unexpected mesh opening'
    (output/'surface.msh').rename(output/'closed_surface.msh')
    gmsh.model.removePhysicalGroups()
    group = gmsh.model.addPhysicalGroup(2, keep)
    gmsh.model.setPhysicalName(2, group, 'OpenTipWing')
    gmsh.option.setNumber('Mesh.SaveAll', 0)
    gmsh.write(str(output/'surface.msh'))
    return len(triangles), len(boundary)


def geometry_audit(shape, output=None):
    """Distance to a continuous reference section, not to its mesh nodes.

    This read-only measurement does not alter the WingCAD BRep or the mesh.
    """
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
    from scipy.interpolate import UnivariateSpline
    y = 622.3  # Mid-semispan section, millimetres.
    section = BRepAlgoAPI_Section(shape, gp_Pln(gp_Pnt(0, y, 0), gp_Dir(0, 1, 0)), False)
    section.Build()
    assert section.IsDone()
    data = np.loadtxt(ROOT/'data/airfoils/rae101.csv', delimiter=',', skiprows=1)
    leading = np.argmin(data[:, 0])
    x = (1-np.cos(np.linspace(0, np.pi, 401)))/2
    distances, records = [], []
    for side_index, side in enumerate((data[:leading+1][::-1], data[leading:])):
        spline = UnivariateSpline(side[:, 0], side[:, 1], k=5, s=1e-8)
        for xi, zi in zip(x, spline(x)):
            vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(float(y+497.84*xi), y, float(497.84*zi))).Vertex()
            distance = BRepExtrema_DistShapeShape(vertex, section.Shape())
            assert distance.IsDone()
            distances.append(float(distance.Value()))
            point = distance.PointOnShape2(1)
            records.append((side_index, xi, zi, (point.X()-y)/497.84,
                            point.Z()/497.84, distance.Value()))
    if output is not None:
        np.savetxt(output/'profile_distances.csv', records, delimiter=',', comments='',
                   header='side_0_upper,reference_x_c,reference_z_c,nearest_CAD_x_c,nearest_CAD_z_c,distance_mm')
    return dict(section_y_mm=y, samples=len(distances),
                max_reference_to_CAD_distance_mm=max(distances),
                rms_reference_to_CAD_distance_mm=float(np.sqrt(np.mean(np.square(distances)))),
                metric='One-way distance from dense continuous reference profile to CAD plane section; not Hausdorff')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'exports/flowpanel/weber/independent')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f'Existing study preserved: {output}')
    source = ROOT/'examples/08_weber_swept_wing.wingcad'
    wing = json.loads(source.read_text())['documento']['objetos'][0]
    assert wing['parametros']['perfil_raiz'] == wing['parametros']['perfil_punta'] == 'RAE101'
    for key, expected in dict(cuerda_raiz_mm=497.84, cuerda_punta_mm=497.84,
                              semi_span_mm=1244.6, flecha_grados=45., diedro_grados=0.,
                              torsion_punta_grados=0.).items():
        assert np.isclose(wing['parametros'][key], expected), f'Changed benchmark geometry: {key}'
    assert all(value == 0 for value in wing['placement'].values()), 'Benchmark placement must be zero'
    app = AeroApplication(); app.abrir_proyecto(source)
    shape = app.documento.objetos[0].shape
    output.mkdir(parents=True)
    (output/'source.wingcad').write_bytes(source.read_bytes())
    step = output/'analysis.step'
    exportar_step(shape, step)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    step_hash = hashlib.sha256(step.read_bytes()).hexdigest()
    audit = geometry_audit(shape, output)
    audit.update(source=str(source.relative_to(ROOT)), source_sha256=source_hash,
                 step_sha256=step_hash, mesher='Gmsh independent unstructured Delaunay',
                 reference_nodes_used=False, refinement_ratio=1.5,
                 fixed_CAD=True, fixed_size_field_distances_m=[.04, .6])
    (output/'geometry_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    import gmsh
    gmsh.initialize(['independent-weber'], readConfigFiles=False)
    try:
        gmsh.option.setNumber('General.NumThreads', 1)
        for level, sizes in SIZES.items():
            folder = output/level; folder.mkdir()
            LEVELS[level] = sizes
            mesh_level(gmsh, step, wing, level, folder, source_hash)
            panels, boundary = remove_caps(gmsh, folder)
            config = tomllib.loads((folder/'case.toml').read_text())
            assert config['signed_volume_m3'] > 0, 'Unexpected inward orientation'
            config.update(panels=panels, tip_caps=False, solver_formulation='direct_open_surface',
                          parent_closed_volume_m3=config.pop('signed_volume_m3'), normal_sign=1,
                          speed_mps=30., aoa_deg=4.2, moment_reference_m=[.12446, 0., 0.],
                          step_sha256=step_hash, mesh_size_max_m=sizes[0], mesh_size_min_m=sizes[1],
                          open_boundary_edges=boundary, gmsh_version=gmsh.__version__,
                          mesh_sha256=hashlib.sha256((folder/'surface.msh').read_bytes()).hexdigest())
            assert panels <= 18000, 'Study exceeds its dense-solver panel budget'
            (folder/'case.toml').write_text(''.join(f'{k} = {json.dumps(v)}\n' for k, v in config.items()), encoding='utf-8')
            print(f'{level}: {panels} open-tip panels; topology verified', flush=True)
    finally:
        gmsh.finalize()
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
