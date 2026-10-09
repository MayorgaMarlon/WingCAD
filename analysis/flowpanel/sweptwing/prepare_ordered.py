"""Independent cosine-distributed mesh sampled from WingCAD's actual BRep.

No FLOWPanel geometry, profile interpolation or reference nodes are used.
Restricted to the constant-chord, untwisted Weber benchmark.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
from OCP.GCPnts import GCPnts_AbscissaPoint

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from app.application import AeroApplication
from core.flowpanel_workflow import validate_weber_document
from core.exporter import exportar_step
from analysis.flowpanel.sweptwing.mesh_quality import mirrored_cells, quality, stations, tip_caps

COUNTS = {'coarse': (16, 12), 'medium': (24, 18), 'fine': (36, 27), 'ultra': (54, 40),
          'extended': (60, 45), 'verification': (66, 50)}


def cad_contour(shape, count, spacing='cosine', metric='chord'):
    y = 622.3
    section = BRepAlgoAPI_Section(shape, gp_Pln(gp_Pnt(0, y, 0), gp_Dir(0, 1, 0)))
    section.Build()
    assert section.IsDone()
    explorer = TopExp_Explorer(section.Shape(), TopAbs_EDGE)
    sides = {}
    x = 497.84*stations(count,spacing)
    while explorer.More():
        curve = BRepAdaptor_Curve(TopoDS.Edge_s(explorer.Current()))
        lo, hi = curve.FirstParameter(), curve.LastParameter()
        start, end = curve.Value(lo), curve.Value(hi)
        assert abs(abs(start.X()-end.X())-497.84) < 1e-5
        length = GCPnts_AbscissaPoint.Length_s(curve,lo,hi) if metric=='arc' else None
        points = []
        for i, xi in enumerate(x):
            if i in (0, count):
                point = min((start, end), key=lambda p: abs(p.X()-y-xi))
            else:
                if metric=='arc':
                    fraction=xi/497.84
                    if start.X()>end.X():fraction=1-fraction
                    parameter=brentq(lambda t:GCPnts_AbscissaPoint.Length_s(curve,lo,t)-length*fraction,lo,hi,xtol=1e-10)
                else:
                    parameter = brentq(lambda t: curve.Value(t).X()-y-xi, lo, hi, xtol=1e-10)
                point = curve.Value(parameter)
            points.append([point.X()-y, point.Z()])
        sides['upper' if curve.Value((lo+hi)/2).Z() > 0 else 'lower'] = np.array(points)
        explorer.Next()
    assert set(sides) == {'upper', 'lower'}
    assert np.max(abs(sides['upper'][[0, -1]]-sides['lower'][[0, -1]])) < 1e-6
    return np.vstack((sides['lower'][::-1], sides['upper'][1:-1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'examples/08_weber_swept_wing.wingcad')
    parser.add_argument('--output', type=Path, default=ROOT/'exports/flowpanel/weber/ordered')
    parser.add_argument('--levels', nargs='+', choices=COUNTS, default=list(COUNTS)[:4])
    parser.add_argument('--append', action='store_true', help='Add fresh levels to an unchanged study')
    parser.add_argument('--connected', action='store_true', help='Share root nodes in one continuous full-wing grid')
    parser.add_argument('--pressure-mode', choices=('least_squares','legacy_flowpanel'),default='least_squares')
    parser.add_argument('--resolutions', nargs='+', help='Independent named resolutions NAME:CHORD_PER_SIDE:HALF_SPAN')
    parser.add_argument('--triangulation', choices=('structured','mirrored_shortest'), default='structured')
    parser.add_argument('--spacing', choices=('cosine','bounded'), default='cosine')
    parser.add_argument('--contour-metric',choices=('chord','arc'),default='chord',help='Place profile nodes by x/c or by actual CAD curve length')
    parser.add_argument('--closed-tips',action='store_true',help='Separate diagnostic: include the CAD tip faces, unlike the open-tip tutorial')
    args = parser.parse_args(); output = args.output.resolve()
    counts = {name:COUNTS[name] for name in args.levels}
    if args.resolutions:
        counts = {}
        for specification in args.resolutions:
            name, chord, span = specification.split(':')
            assert name.replace('_','').isalnum() and name not in counts
            counts[name] = (int(chord),int(span))
            assert min(counts[name]) >= 4
    if args.triangulation != 'structured' and (not args.connected or args.pressure_mode != 'least_squares'):
        parser.error('Mirrored connectivity requires a connected grid and topology-aware least squares')
    if args.closed_tips and args.triangulation != 'mirrored_shortest':
        parser.error('Closed tip diagnostic requires mirrored_shortest triangulation')
    if args.pressure_mode == 'least_squares' and not args.connected:
        parser.error('least_squares requires --connected; use --pressure-mode legacy_flowpanel only for diagnostic half-body runs')
    if output.exists() and not args.append: raise FileExistsError(output)
    source = args.source.resolve()
    document = json.loads(source.read_text(encoding='utf-8'))
    validate_weber_document(document)
    wing = document['documento']['objetos'][0]
    p = wing['parametros']
    assert p['perfil_raiz'] == p['perfil_punta'] == 'RAE101'
    for key, value in dict(cuerda_raiz_mm=497.84, cuerda_punta_mm=497.84,
                           semi_span_mm=1244.6, flecha_grados=45., diedro_grados=0., torsion_punta_grados=0.).items():
        assert np.isclose(p[key], value), key
    assert all(v == 0 for v in wing['placement'].values())
    app = AeroApplication(); app.abrir_proyecto(source); shape = app.documento.objetos[0].shape
    if args.append:
        assert (output/'source.wingcad').read_bytes() == source.read_bytes(), 'CAD source changed'
        assert all(not (output/level).exists() for level in counts), 'Existing levels preserved'
    else:
        output.mkdir(parents=True); exportar_step(shape, output/'analysis.step')
        (output/'source.wingcad').write_bytes(source.read_bytes())
    criteria = dict(CL_relative_percent=1., CD_relative_percent=5., Cp_rms=.02, Cp_p95=.05,
                    pressure_domain='0.01 <= x/c <= 0.99; 0.05 <= abs(2y/b) <= 0.95',
                    required_successive_passing_pairs=2, convergence_type='engineering mesh sensitivity, not a continuum error bound')
    if args.append:
        assert json.loads((output/'criteria.json').read_text()) == criteria, 'Criteria changed'
    else:
        (output/'criteria.json').write_text(json.dumps(criteria, indent=2))
    for level,(nc,ns) in counts.items():
        folder = output/level; folder.mkdir()
        contour = cad_contour(shape, nc,args.spacing,args.contour_metric)
        span = 1244.6*(1-stations(ns,args.spacing))
        maxdist = 0.
        halves = []
        for side, sign in (('L', -1), ('R', 1)):
            nodes = np.array([[x+y, sign*y, z] for y in span for x, z in contour])
            for point in nodes[::max(1, len(nodes)//100)]:
                distance = BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(gp_Pnt(*point)).Vertex(), shape)
                assert distance.IsDone() and distance.Value() < 1e-3, f'CAD sampling distance: {distance.Value()} mm'
                maxdist = max(maxdist, distance.Value())
            np.savetxt(folder/f'nodes_{side}.csv', nodes/1000, delimiter=',', fmt='%.17g')
            halves.append(nodes)
        if args.connected:
            right = halves[1].reshape(ns+1,2*nc,3)[::-1]
            assert np.max(abs(halves[0][-2*nc:]-right[0])) < 1e-9
            full = np.vstack((halves[0],right[1:].reshape(-1,3)))
            np.savetxt(folder/'nodes_C.csv',full/1000,delimiter=',',fmt='%.17g')
            if args.triangulation == 'mirrored_shortest':
                cells = mirrored_cells(full/1000,2*nc,ns)
                if args.closed_tips:
                    cells = np.vstack((cells,tip_caps(full/1000,2*nc,ns)))
                np.savetxt(folder/'cells_C.csv',cells+1,delimiter=',',fmt='%d')
                (folder/'mesh_quality.json').write_text(json.dumps(quality(full/1000,cells),indent=2))
        config = dict(adapter='weber_ordered', units='m', level=level, contour_intervals=2*nc, span_intervals=ns, panels=8*nc*ns+(4*nc-4 if args.closed_tips else 0),
                      source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                      maximum_sampled_node_CAD_distance_mm=maxdist,
                      first_chord_interval_mm=float(contour[nc-1,0]-contour[nc,0]),
                      smallest_span_interval_mm=float(min(abs(np.diff(span)))),
                      speed_mps=30., aoa_deg=4.2, density_kg_m3=1.225, bref_m=2.4892,
                      sref_m2=2.4892*.49784, reference_nodes_used=False, connected_root=args.connected,
                      pressure_reconstruction=args.pressure_mode,triangulation=args.triangulation,
                      spacing=args.spacing,closed_tips=args.closed_tips,contour_metric=args.contour_metric)
        (folder/'case.toml').write_text(''.join(f'{k} = {json.dumps(v)}\n' for k,v in config.items()))
        print(level, config['panels'], maxdist, flush=True)


if __name__ == '__main__': main()
