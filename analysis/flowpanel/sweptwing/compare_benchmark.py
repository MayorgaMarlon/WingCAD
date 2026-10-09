"""Compare independent CAD meshes with the tutorial and its refinements, headless."""
import csv
import hashlib
import html
import json
from pathlib import Path
import sys
import tomllib

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from analysis.flowpanel.sweptwing.compare import read_vtk, section, loading, B, C, Q, L, D
from analysis.flowpanel.sweptwing.compare_ordered import sample_panels

BASE = ROOT / 'exports/flowpanel/weber'
OUT = Path(__file__).parent / 'results/benchmark'


def write_csv(name, header, rows):
    with (OUT/name).open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    datasets, configs, provenance = {}, {}, []
    cases = [('FLOWPanel tutorial', BASE/'reference', True),
             ('FLOWPanel refined 1', BASE/'reference_r12_s23', True),
             ('FLOWPanel refined 2', BASE/'reference_r18_s34', True)]
    cases += [(f'WingCAD {level}', BASE/'chord_resolved'/level/'results', False)
              for level in ('coarse', 'medium', 'fine')]
    for name, folder, reference in cases:
        files = [folder/f'reference_{side}.vtk' for side in ('L', 'R')] if reference else [folder/'wing_C.vtk']
        parts = [read_vtk(p) for p in files]
        datasets[name] = tuple(np.concatenate([p[i] for p in parts]) for i in range(3))
        cfg = tomllib.loads((folder/'coefficients.toml').read_text(encoding='utf-8'))
        for key, value in dict(speed_mps=30., aoa_deg=4.2, density_kg_m3=1.225,
                               bref_m=B, sref_m2=B*C).items():
            assert np.isclose(cfg[key], value), (name, key)
        tri, cp, forces = datasets[name]
        assert len(tri) == cfg['panels']
        for key, direction in [('CL', L), ('CD_inviscid', D)]:
            assert np.isclose(forces.sum(axis=0)@direction/(Q*B*C), cfg[key], rtol=1e-7)
        if not reference:
            assert not cfg['reference_nodes_used'] and not cfg['closed_tips']
            assert cfg['pressure_reconstruction'] == 'least_squares'
        configs[name] = cfg
        for p in files+[folder/'coefficients.toml']:
            provenance.append(dict(path=str(p.relative_to(ROOT)), sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    assert len({v['flowpanel_version'] for v in configs.values()}) == 1
    colors = dict(zip(datasets, ['#111111', '#777777', '#b36c00', '#86b8df', '#287fb4', '#bc2852']))
    styles = {n: '--' if n.startswith('FLOWPanel') else '-' for n in datasets}
    exp = json.loads((Path(__file__).parent/'experimental.json').read_text())
    coefficients = []
    ref = configs['FLOWPanel tutorial']
    for name, cfg in configs.items():
        coefficients.append([name, cfg['panels'], cfg['CL'], cfg['CD_inviscid'],
                             100*(cfg['CL']/ref['CL']-1), 100*(cfg['CD_inviscid']/ref['CD_inviscid']-1)])
    write_csv('coefficients.csv', ['case', 'panels', 'CL', 'CD_inviscid', 'CL_difference_tutorial_percent', 'CD_difference_tutorial_percent'], coefficients)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for prefix in ('FLOWPanel', 'WingCAD'):
        selected = [v for n, v in configs.items() if n.startswith(prefix)]
        for ax, key in zip(axes, ('CL', 'CD_inviscid')):
            ax.plot([c['panels'] for c in selected], [c[key] for c in selected], 'o-', label=prefix)
            ax.set(xlabel='Panels', ylabel=key); ax.grid(alpha=.2); ax.legend()
    fig.tight_layout(); fig.savefig(OUT/'coefficients.png', dpi=160); plt.close(fig)
    records = []
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharex=True, sharey=True)
    for ax, eta in zip(axes.flat, (.041, .163, .245, .510)):
        for name, (tri, cp, _) in datasets.items():
            for side, pts in enumerate(section(tri, cp, eta)):
                ax.plot(pts[:, 0], pts[:, 1], styles[name], color=colors[name], lw=1,
                        label=name if side == 0 else None)
                records.extend((name, eta, 'upper' if side == 0 else 'lower', x, v) for x, v in pts)
        key = min(exp['Cp'], key=lambda k: abs(float(k)-eta))
        for side, xkey in enumerate(('weber_xoc_up', 'weber_xoc_lo')):
            ax.scatter(exp[xkey], [np.nan if v is None else v for v in exp['Cp'][key][side]],
                       c='black', s=12, label='Experimental' if side == 0 else None)
        ax.set(title=f'2y/b = {eta}', xlabel='x/c', ylabel='Cp'); ax.grid(alpha=.2)
    axes[0, 0].invert_yaxis(); axes[0, 0].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(OUT/'pressure_sections.png', dpi=180)
    axes[0, 0].set_ylim(1, -1)
    fig.suptitle('Detail view: Cp axis limited to [-1, 1]; full range in companion plot')
    fig.tight_layout(); fig.savefig(OUT/'pressure_sections_detail.png', dpi=180); plt.close(fig)
    write_csv('pressure_sections.csv', ['case', 'eta', 'surface', 'x_over_c', 'Cp'], records)
    # Sample raw constant panel values at identical interior coordinates; no smoothing.
    x = np.linspace(.001, .999, 300)
    delta_records = []
    fig, axes = plt.subplots(5, 2, figsize=(13, 17), sharex=True, sharey=True)
    for ax, eta in zip(axes.flat, (0., .04, .08, .16, .24, .51, .65, .9, .95)):
        for name, (tri, cp, _) in datasets.items():
            centers = tri.mean(axis=1)
            vals = []
            for sign in (1, -1):
                mask = (centers[:, 1] > 0) & (centers[:, 2]*sign > 0)
                vals.append(sample_panels(tri[mask], cp[mask], x, np.full_like(x, max(eta, 1e-7))))
            assert np.isfinite(vals).all(), (name, eta)
            delta = vals[0]-vals[1]
            ax.plot(x, delta, styles[name], color=colors[name], lw=.9, label=name)
            delta_records.extend((name, eta, a, u, lo, u-lo) for a, u, lo in zip(x, *vals))
        experimental = np.loadtxt(Path(__file__).parent/f'weber1958-fig2-y2b-{round(eta*100):03}.csv', delimiter=',')
        ax.scatter(*experimental.T, c='black', s=12)
        ax.set(title=f'2y/b = {eta}', xlabel='x/c', ylabel='Cp upper - Cp lower'); ax.grid(alpha=.2)
    axes[0, 0].invert_yaxis(); axes[0, 0].legend(fontsize=7); axes[-1, -1].axis('off')
    fig.tight_layout(); fig.savefig(OUT/'delta_cp.png', dpi=160); plt.close(fig)
    write_csv('delta_cp.csv', ['case', 'eta', 'x_over_c', 'Cp_upper', 'Cp_lower', 'delta_Cp'], delta_records)
    edges = np.linspace(-B/2, B/2, 31); edges[0] -= 1e-9; edges[-1] += 1e-9
    span_records = []
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for name, (tri, _, forces) in datasets.items():
        values = loading(tri, forces, edges)
        eta = (edges[:-1]+edges[1:])/B
        for j, ax in enumerate(axes):
            ax.plot(eta, values[:, j], styles[name], color=colors[name], label=name)
        span_records.extend((name, lo, hi, e, cl, cd) for lo, hi, e, (cl, cd) in zip(edges[:-1], edges[1:], eta, values))
    for ax, key, ylabel in zip(axes, ('cls_web', 'cds_web'), ('Sectional cl', 'Sectional cd')):
        ys = np.array(exp['y2b_web']); v = np.array(exp[key])
        ax.scatter(np.r_[-ys[::-1], ys], np.r_[v[::-1], v], c='black', s=14, label='Experimental')
        ax.set(xlabel='2y/b', ylabel=ylabel); ax.grid(alpha=.2); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(OUT/'spanwise_loading.png', dpi=180); plt.close(fig)
    write_csv('spanwise_loading.csv', ['case', 'y_lower_m', 'y_upper_m', 'eta', 'cl', 'cd'], span_records)
    samples = {}
    xx, ee = np.meshgrid(np.linspace(.01, .99, 121), np.linspace(.05, .95, 25))
    for name, (tri, cp, _) in datasets.items():
        centers = tri.mean(axis=1)
        values = []
        for sign in (1, -1):
            mask = (centers[:, 1] > 0) & (centers[:, 2]*sign > 0)
            values.append(sample_panels(tri[mask], cp[mask], xx, ee))
        samples[name] = np.array(values)
        assert np.isfinite(samples[name]).all()
    pairs = []
    for prefix in ('FLOWPanel', 'WingCAD'):
        names = [n for n in configs if n.startswith(prefix)]
        for old, new in zip(names, names[1:]):
            delta = samples[new]-samples[old]
            pairs.append([old, new, *[100*abs(configs[new][k]/configs[old][k]-1) for k in ('CL', 'CD_inviscid')],
                          float(np.sqrt(np.mean(delta**2))), float(np.quantile(abs(delta), .95))])
    write_csv('refinement.csv', ['old', 'new', 'CL_change_percent', 'CD_change_percent', 'Cp_RMS', 'Cp_p95'], pairs)
    audit = dict(configurations=configs, inputs=provenance,
                 note='Nominal geometry and operating conditions match; surface representation, topology and pressure reconstruction differ. Not an isolated geometry-error measurement.')
    (OUT/'audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    rows = ''.join('<tr>'+''.join(f'<td>{html.escape(str(v)) if isinstance(v,str) else f"{v:.7g}"}</td>' for v in r)+'</tr>' for r in coefficients)
    pair_rows = ''.join('<tr>'+''.join(f'<td>{html.escape(str(v)) if isinstance(v,str) else f"{v:.4f}"}</td>' for v in r)+'</tr>' for r in pairs)
    text = f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>WingCAD / FLOWPanel: comparación</title>
<style>body{{font:17px system-ui;max-width:1250px;margin:35px auto;padding:15px;color:#183047}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;border-bottom:1px solid #ccc;text-align:left}}img{{width:100%}}.note{{background:#fff0cf;padding:18px}}</style>
<h1>Ala Weber: WingCAD / FLOWPanel</h1><p>RAE101 · b=2,4892 m · c=0,49784 m · flecha 45° · 30 m/s · AoA 4,2° · 1,225 kg/m³ · S=1,239223328 m².</p>
<p class="note"><strong>Comparación preliminar: sin convergencia demostrada.</strong> WingCAD conserva el método lineal de presión y sus mallas independientes. No se ajustaron nodos ni coeficientes a la referencia. Las diferencias porcentuales son respecto al tutorial de malla finita, no errores exactos.</p>
<table><tr><th>Caso</th><th>Paneles</th><th>CL</th><th>CD inviscido</th><th>ΔCL %</th><th>ΔCD %</th></tr>{rows}</table>
<p>Experimental del ejemplo: CL={exp['CL']}; CD={exp['CD']}. El CD experimental incluye efectos físicos que este modelo inviscido no representa.</p>
<h2>Auditoría de equivalencia</h2><p>Mismo perfil nominal, cuerda constante, sin torsión ni diedro, condiciones y normalización verificadas. Ambos usan puntas abiertas y estela rígida alineada con el flujo. WingCAD muestrea su BRep; FLOWPanel usa su representación del perfil. La referencia conserva dos semialas y su reconstrucción original; WingCAD comparte nodos en la raíz y usa vecinos reales para reconstruir la presión. Por ello la diferencia incluye discretización, representación geométrica y tratamiento numérico: no se atribuye sólo a la geometría.</p>
<h2>Sensibilidad de resolución</h2><table><tr><th>Anterior</th><th>Siguiente</th><th>Cambio CL %</th><th>Cambio CD %</th><th>Cp RMS</th><th>Cp p95</th></tr>{pair_rows}</table>
<p>Los criterios WingCAD siguen siendo dos pares sucesivos con CL ≤1%, CD ≤5%, Cp RMS ≤0,02 y p95 ≤0,05 en el dominio interior. Las pequeñas variaciones integrales de referencia por sí solas no prueban convergencia local. Sus refinamientos son aproximadamente 1,5 por dirección, con redondeo entero.</p>
<img src="coefficients.png" alt="Coeficientes por resolución">
<h2>Presión a lo largo de la cuerda</h2><p>Cortes en las estaciones del ejemplo; valores originales de panel. Las líneas unen muestras sin filtrado.</p><img src="pressure_sections.png" alt="Cp completo"><p>Vista ampliada con eje Cp limitado a [?1, 1], ?nicamente para leer las curvas. Los extremos permanecen en la figura anterior y los CSV.</p><img src="pressure_sections_detail.png" alt="Detalle de Cp">
<h2>Diferencia de presión</h2><p>Cp superior menos Cp inferior, evaluados en los mismos x/c con el valor constante del triángulo que contiene cada punto. La estación de raíz se evalúa en 2y/b=10⁻⁷. Sin suavizado ni recorte de extremos.</p><img src="delta_cp.png" alt="Delta Cp">
<h2>Carga a lo largo de la envergadura</h2><p>Integración conservativa por franjas comunes: cada panel aporta la fracción de área que intersecta la franja. Se comprueba que las fuerzas suman los coeficientes guardados.</p><img src="spanwise_loading.png" alt="Cargas">
<h2>Datos descargables</h2><p>'''
    text += ' · '.join(f'<a href="{p.name}">{p.name}</a>' for p in sorted(OUT.glob('*.csv')))
    text += ' · <a href="audit.json">Configuraciones y hashes</a> · <a href="../directional/report.html">Refinamiento separado de cuerda y envergadura</a></p></html>'
    (OUT/'report.html').write_text(text, encoding='utf-8')
    print(json.dumps(dict(coefficients=coefficients, refinement=pairs), indent=2))


if __name__ == '__main__':
    main()
