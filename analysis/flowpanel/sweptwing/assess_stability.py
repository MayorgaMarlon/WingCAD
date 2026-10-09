"""WingCAD-only directional refinement: fixed CAD, pressure method and criteria."""
from pathlib import Path
import csv
import hashlib
import json
import sys
import tomllib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from analysis.flowpanel.sweptwing.reconstruct_pressure import load_fields
from analysis.flowpanel.sweptwing.compare_ordered import sample_panels
from analysis.flowpanel.sweptwing.wake_forces import from_solution
from analysis.flowpanel.sweptwing.compare import B, C, Q, L, D


def main():
    base = ROOT/'exports/flowpanel/weber'
    output = Path(__file__).parent/'results/stability'
    output.mkdir(parents=True, exist_ok=True)
    cases = {}
    samples = {}
    provenance = []
    x, eta = np.meshgrid(np.linspace(.01, .99, 121), np.linspace(.05, .95, 25))
    for nc in (36, 54, 72, 108):
        for ns in ((16, 24, 36, 54) if nc == 72 else (16, 24, 36)):
            key = f'c{nc}_s{ns}'
            if nc <= 54:
                folder = base/'directional_bounded'/key
            elif (nc, ns) == (72, 24):
                folder = base/'chord_resolved/medium'
            elif (nc, ns) == (108, 36):
                folder = base/'chord_resolved/fine'
            else:
                folder = base/'stability_cross'/key
            cfg = tomllib.loads((folder/'results/coefficients.toml').read_text())
            assert cfg['contour_intervals'] == 2*nc and cfg['span_intervals'] == ns
            for k, v in dict(connected_root=True, closed_tips=False, spacing='bounded',
                             pressure_reconstruction='least_squares', triangulation='mirrored_shortest',
                             reference_nodes_used=False).items():
                assert cfg.get(k, False if k == 'closed_tips' else None) == v, (key, k)
            assert cfg.get('contour_metric', 'chord') == 'chord'
            assert cfg['normal_velocity_residual_mps']/cfg['speed_mps'] < 1e-8
            nodes, cells, fields = load_fields(folder/'results/wing_C.vtk')
            tri = nodes[cells]; centers = tri.mean(axis=1)
            force = fields['F']
            for name, direction in [('CL', L), ('CD_inviscid', D)]:
                assert np.isclose(force.sum(axis=0)@direction/(Q*B*C), cfg[name], rtol=1e-7)
            values = []
            for sign in (1, -1):
                mask = (centers[:, 1] > 0) & (centers[:, 2]*sign > 0)
                values.append(sample_panels(tri[mask], fields['Cp'][mask], x, eta))
            samples[key] = np.array(values)
            assert np.isfinite(samples[key]).all()
            cfg.update(from_solution(nodes, cells, fields, cfg))
            worst = centers[int(np.argmin(fields['Cp']))]
            cfg['Cp_min_abs_eta'] = float(2*abs(worst[1])/B)
            cfg['Cp_min_x_over_c'] = float((worst[0]-abs(worst[1]))/C)
            tip = abs(2*centers[:, 1]/B) > .95
            cfg['CD_outer_5_percent'] = float(force[tip].sum(axis=0)@D/(Q*B*C))
            cfg['CD_inner_95_percent'] = float(force[~tip].sum(axis=0)@D/(Q*B*C))
            cases[key] = cfg
            for p in (folder/'results/coefficients.toml', folder/'results/wing_C.vtk'):
                provenance.append(dict(path=str(p.relative_to(ROOT)), sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    for field in ('source_sha256', 'speed_mps', 'aoa_deg', 'density_kg_m3', 'bref_m', 'sref_m2', 'flowpanel_version'):
        assert len({c[field] for c in cases.values()}) == 1, field
    criteria = json.loads((base/'chord_resolved/criteria.json').read_text())
    pairs = []
    sequences = [('chord', f's{ns}', [f'c{nc}_s{ns}' for nc in (36, 54, 72, 108)]) for ns in (16, 24, 36)]
    sequences += [('span', f'c{nc}', [f'c{nc}_s{ns}' for ns in ((16, 24, 36, 54) if nc == 72 else (16, 24, 36))]) for nc in (36, 54, 72, 108)]
    sequence_passes = []
    for direction, fixed, names in sequences:
        checks = []
        for old, new in zip(names, names[1:]):
            delta = samples[new]-samples[old]
            metrics = dict(CL_relative_percent=100*abs(cases[new]['CL']/cases[old]['CL']-1),
                           CD_relative_percent=100*abs(cases[new]['CD_inviscid']/cases[old]['CD_inviscid']-1),
                           Cp_rms=float(np.sqrt(np.mean(delta**2))), Cp_p95=float(np.quantile(abs(delta), .95)))
            passed = all(v <= criteria[k] for k, v in metrics.items())
            checks.append(passed)
            pairs.append(dict(direction=direction, fixed=fixed, old=old, new=new, **metrics, passed=passed))
        sequence_passes.append(dict(direction=direction, fixed=fixed,
                                    two_successive_passes=len(checks)>=2 and all(checks[-2:])))
    simultaneous = json.loads((base/'chord_resolved/comparison/convergence.json').read_text())
    summary = dict(simultaneous_refinement_passed=simultaneous['engineering_convergence_passed'], criteria=criteria, cases=cases, pairs=pairs, sequences=sequence_passes, inputs=provenance,
                   note='Directional stability is not simultaneous refinement convergence or a continuum error bound.')
    (output/'audit.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    keys = ['panels', 'CL', 'CD_inviscid', 'CL_wake', 'CD_trefftz', 'Cp_min', 'Cp_min_abs_eta', 'CD_outer_5_percent', 'CD_inner_95_percent']
    with (output/'coefficients.csv').open('w', newline='') as f:
        w = csv.writer(f); w.writerow(['case']+keys)
        w.writerows([name]+[v[k] for k in keys] for name, v in cases.items())
    with (output/'refinement.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(pairs[0])); w.writeheader(); w.writerows(pairs)
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    for col, coefficient in enumerate(('CL', 'CD_inviscid')):
        for ns in (16, 24, 36):
            axes[0, col].plot((36, 54, 72, 108), [cases[f'c{nc}_s{ns}'][coefficient] for nc in (36, 54, 72, 108)], 'o-', label=f'span={ns}')
        for nc in (36, 54, 72, 108):
            spans = (16, 24, 36, 54) if nc == 72 else (16, 24, 36)
            axes[1, col].plot(spans, [cases[f'c{nc}_s{ns}'][coefficient] for ns in spans], 'o-', label=f'chord={nc}')
        for row, label in enumerate(('Chord intervals per surface', 'Span intervals per half-wing')):
            axes[row, col].set(xlabel=label, ylabel=coefficient); axes[row, col].grid(alpha=.2); axes[row, col].legend()
    fig.tight_layout(); fig.savefig(output/'directional.png', dpi=170); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for nc in (36, 54, 72, 108):
        spans = (16, 24, 36, 54) if nc == 72 else (16, 24, 36)
        for ax, quantity in zip(axes, ('Cp_min', 'CD_outer_5_percent')):
            ax.plot(spans, [cases[f'c{nc}_s{ns}'][quantity] for ns in spans], 'o-', label=f'chord={nc}')
            ax.set(xlabel='Span intervals per half-wing', ylabel=quantity); ax.grid(alpha=.2); ax.legend()
    fig.tight_layout(); fig.savefig(output/'tip_sensitivity.png', dpi=170); plt.close(fig)
    rows = ''.join(f'<tr><td>{n}</td>'+''.join(f'<td>{v[k]:.7g}</td>' for k in keys)+'</tr>' for n, v in cases.items())
    checks = ''.join(f'<tr><td>{p["direction"]}: {p["old"]} → {p["new"]}</td>'+''.join(f'<td>{p[k]:.5g}</td>' for k in ('CL_relative_percent', 'CD_relative_percent', 'Cp_rms', 'Cp_p95'))+f'<td>{p["passed"]}</td></tr>' for p in pairs)
    sequence_rows = ''.join(f'<li>{p["direction"]}, {p["fixed"]}: {p["two_successive_passes"]}</li>' for p in sequence_passes)
    final_pair = next(p for p in pairs if p['old']=='c72_s36' and p['new']=='c72_s54')
    html = f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>Estabilidad propia de WingCAD</title>
<style>body{{font:16px system-ui;max-width:1350px;margin:30px auto;padding:15px;color:#183047}}td,th{{padding:9px;border-bottom:1px solid #ccc}}table{{border-collapse:collapse}}img{{width:100%}}</style>
<h1>WingCAD: refinamiento independiente de cuerda y envergadura</h1>
<p><strong>Resultado: la estabilidad global mejora, pero la presión local todavía falla.</strong> En la extensión c72_s36 → c72_s54, CL cambia {final_pair['CL_relative_percent']:.3f}% y CD {final_pair['CD_relative_percent']:.3f}%; Cp RMS={final_pair['Cp_rms']:.6f}, frente al límite 0,02. El Cp mínimo pasa de {cases['c72_s36']['Cp_min']:.3f} a {cases['c72_s54']['Cp_min']:.3f}, en ambos casos junto a la punta. No se declara convergencia.</p>
<p>Mismo CAD, condiciones, puntas abiertas, raíz conectada, distribución bounded, triangulación simétrica y reconstrucción lineal de presión. No se usa FLOWPanel de referencia como objetivo de ajuste.</p>
<p>Las filas exploran resolución de cuerda y las columnas envergadura por separado. No basta que una dirección se estabilice: la otra puede seguir cambiando el resultado. Las últimas dos parejas deben cumplir CL ≤1%, CD ≤5%, Cp RMS ≤0,02 y p95 ≤0,05. Dominio local: x/c=0,01…0,99 y 2y/b=0,05…0,95; extremos excluidos sólo de ese criterio local, nunca de la fuerza total.</p>
<h2>Resultado de las últimas dos parejas por dirección</h2><ul>{sequence_rows}</ul><p>El ensayo previo de refinamiento simultáneo conserva su resultado: {simultaneous["engineering_convergence_passed"]}. No se reemplaza por una secuencia más favorable.</p><img src="directional.png" alt="Sensibilidad de WingCAD">
<table><tr><th>Caso</th>{''.join(f'<th>{k}</th>' for k in keys)}</tr>{rows}</table>
<p>CL_wake y CD_trefftz son diagnósticos de la circulación y estela rígida. No reemplazan ni corrigen los coeficientes integrados de presión. La contribución exterior es una descomposición de la fuerza original, no un recorte.</p>
<h2>Sensibilidad local y contribución de las puntas</h2><img src="tip_sensitivity.png" alt="Cp mínimo y CD exterior"><p>La división de fuerzas usa el centroide de cada triángulo para asignarlo a la región interior o exterior. Los valores extremos son los originales, sin suavizado. Un total estable puede ocultar compensaciones entre regiones.</p><h2>Criterios por refinamiento</h2><table><tr><th>Pareja</th><th>ΔCL %</th><th>ΔCD %</th><th>Cp RMS</th><th>Cp p95</th><th>Cumple</th></tr>{checks}</table>
<p>Estabilidad direccional no equivale a convergencia simultánea ni a una cota del error continuo. No se declara convergencia completa con este ensayo.</p>
<p><a href="coefficients.csv">Coeficientes CSV</a> · <a href="refinement.csv">Refinamientos CSV</a> · <a href="audit.json">Auditoría y hashes</a></p></html>'''
    (output/'report.html').write_text(html, encoding='utf-8')
    print(json.dumps(dict(sequences=sequence_passes, pairs=pairs), indent=2))


if __name__ == '__main__':
    main()
