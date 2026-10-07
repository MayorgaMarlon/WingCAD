"""Compare independently solved, matched tutorial and WingCAD panel geometries.

Uses the tutorial's nearest span column and triangle-pair averaging for plots.
Raw per-triangle fields are retained and compared before any plot reduction.
"""
import csv
import json
import tomllib
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

from compare import read_vtk, B, C, Q, D, L, DATA, OUT


def column(data, eta):
    tri, cp, _ = data
    centers = tri.mean(axis=1).reshape(15, 48, 2, 3)
    j = np.argmin(abs(centers[:, :, :, 1].mean(axis=(1, 2)) - eta*B/2))
    points = centers[j].mean(axis=1)
    values = cp.reshape(15, 48, 2)[j].mean(axis=1)
    return (points[:, 0]-points[:, 0].min())/C, values, points[:, 1].mean()*2/B


def main():
    output = OUT/'matched_comparison'
    output.mkdir(exist_ok=True)
    labels = ('FLOWPanel tutorial', 'WingCAD + FLOWPanel')
    folders = ('reference', 'wingcad_matched')
    datasets = {label: [read_vtk(OUT/folder/f'reference_{side}.vtk') for side in ('L', 'R')]
                for label, folder in zip(labels, folders)}
    coefficients = {label: tomllib.loads((OUT/folder/'coefficients.toml').read_text())
                    for label, folder in zip(labels, folders)}
    for values in coefficients.values():
        for key, expected in dict(panels=2880, speed_mps=30., aoa_deg=4.2,
                                  density_kg_m3=1.225, bref_m=B, sref_m2=B*C).items():
            assert np.isclose(values[key], expected), key
        assert values['flowpanel_version'] == coefficients[labels[0]]['flowpanel_version']
    differences = {}
    for key in ('CL', 'CD_inviscid'):
        differences[key+'_percent'] = 100*(coefficients[labels[1]][key]/coefficients[labels[0]][key]-1)
    distances, cp_error = [], []
    for original, cad in zip(datasets[labels[0]], datasets[labels[1]]):
        # Matching cell and vertex ordering also detects connectivity changes.
        distances.extend(np.linalg.norm(original[0]-cad[0], axis=2).ravel())
        cp_error.extend(cad[1]-original[1])
    differences.update(max_vertex_difference_m=float(max(distances)),
                       max_abs_Cp_difference=float(np.max(np.abs(cp_error))),
                       rms_Cp_difference=float(np.sqrt(np.mean(np.square(cp_error)))))
    assert differences['max_vertex_difference_m'] < 1e-8
    # Regression acceptance, not a physical accuracy or convergence assertion.
    assert differences['max_abs_Cp_difference'] < 1e-4
    assert abs(differences['CL_percent']) < .01
    assert abs(differences['CD_inviscid_percent']) < .01
    for label, halves in datasets.items():
        force = sum((part[2].sum(axis=0) for part in halves), start=np.zeros(3))
        assert np.isclose(force@L/(Q*B*C), coefficients[label]['CL'], rtol=1e-7)
        assert np.isclose(force@D/(Q*B*C), coefficients[label]['CD_inviscid'], rtol=1e-7)
    exp = json.loads((DATA/'experimental.json').read_text())
    styles = [dict(color='#1976c5', lw=2.6), dict(color='#e57818', lw=1.5, ls='--')]
    records = []
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True, sharey=True)
    for ax, eta in zip(axes.flat, (.041, .163, .245, .510)):
        for (label, halves), style in zip(datasets.items(), styles):
            x, cp, actual = column(halves[1], eta)
            ax.plot(x, cp, label=label, **style)
            records.extend((label, eta, actual, i, a, v) for i, (a, v) in enumerate(zip(x, cp)))
        key = min(exp['Cp'], key=lambda k: abs(float(k)-eta))
        for side, xkey in enumerate(('weber_xoc_up', 'weber_xoc_lo')):
            ax.scatter(exp[xkey], [np.nan if v is None else v for v in exp['Cp'][key][side]],
                       c='black', s=18, label='Experimental' if side == 0 else None, zorder=5)
        ax.set(title=f'2y/b = {eta} (mesh column {actual:.4f})', xlabel='x/c', ylabel='Cp',
               xlim=(-.02, 1.02), ylim=(1, -.9))
        ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('Same geometry, 2,880 panels and flow conditions — chordwise pressure')
    fig.tight_layout(); fig.savefig(output/'chordwise_cp.png', dpi=180); plt.close(fig)
    with (output/'pressure_sections.csv').open('w', newline='') as f:
        writer = csv.writer(f); writer.writerow(('case', 'target_2y/b', 'actual_2y/b', 'index', 'x/c', 'Cp'))
        writer.writerows(records)

    fig, axes = plt.subplots(5, 2, figsize=(11, 15), sharex=True, sharey=True)
    for ax, eta in zip(axes.flat, (0, .04, .08, .16, .24, .51, .65, .9, .95)):
        for (label, halves), style in zip(datasets.items(), styles):
            x, cp, _ = column(halves[1], eta)
            ax.plot((x[:24]+x[:23:-1])/2, cp[:23:-1]-cp[:24], label=label, **style)
        raw = np.loadtxt(DATA/f'weber1958-fig2-y2b-{round(eta*100):03}.csv', delimiter=',')
        ax.scatter(raw[:, 0], raw[:, 1], c='black', s=18, label='Experimental', zorder=5)
        ax.set(title=f'2y/b = {eta}', xlabel='x/c', ylabel='Cp upper − Cp lower', ylim=(.1, -1.2))
        ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8); axes[-1, -1].axis('off')
    fig.tight_layout(); fig.savefig(output/'delta_cp.png', dpi=180); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    loads = []
    for (label, halves), style in zip(datasets.items(), styles):
        rows = []
        for tri, cp, forces in halves:
            centers = tri.mean(axis=1).reshape(15, 96, 3).mean(axis=1)
            # Same center-to-center width convention as calcfield_sectionalforce.
            widths = abs(np.gradient(centers[:, 1]))
            sectional = forces.reshape(15, 96, 3).sum(axis=1)/widths[:, None]/(Q*C)
            rows.extend(zip(centers[:, 1]*2/B, sectional@L, sectional@D))
        rows = np.array(sorted(rows))
        for i, ax in enumerate(axes):
            ax.plot(rows[:, 0], rows[:, i+1], label=label, **style)
        loads.extend((label, *r) for r in rows)
    for ax, key, title in zip(axes, ('cls_web', 'cds_web'), ('Sectional lift cl', 'Sectional drag cd')):
        ys, values = np.array(exp['y2b_web']), np.array(exp[key])
        ax.scatter(np.r_[-ys[::-1], ys], np.r_[values[::-1], values], c='black', s=18, label='Experimental')
        ax.set(xlabel='2y/b', ylabel=title); ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(output/'spanwise_loading.png', dpi=180); plt.close(fig)
    with (output/'spanwise_loading.csv').open('w', newline='') as f:
        writer=csv.writer(f); writer.writerow(('case', '2y/b', 'cl', 'cd')); writer.writerows(loads)

    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    for row, (label, halves) in enumerate(datasets.items()):
        tri = np.concatenate([h[0] for h in halves]); cp = np.concatenate([h[1] for h in halves])
        for col, upper in enumerate((True, False)):
            mask = (tri[:, :, 2].mean(axis=1) > 0) == upper
            vertices = tri[mask][:, :, [1, 0]].copy(); vertices[:, :, 1] *= -1
            pc = PolyCollection(vertices, array=cp[mask], cmap='coolwarm', clim=(-.5, .5), edgecolors='none')
            ax = axes[row, col]; ax.add_collection(pc); ax.autoscale_view(); ax.set_aspect('equal')
            ax.set(title=label+(' — upper' if upper else ' — lower'), xlabel='y (m)', ylabel='−x (m)')
            fig.colorbar(pc, ax=ax, label='Cp (color range ±0.5)', shrink=.6)
    fig.tight_layout(); fig.savefig(output/'pressure_top_bottom.png', dpi=180); plt.close(fig)
    audit = json.loads((OUT/'matched_geometry/geometry_audit.json').read_text())
    summary = dict(coefficients=coefficients, differences=differences, geometry_audit=audit,
                   experimental=dict(CL=.238, CD=.005))
    (output/'comparison.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    rows = ''.join(f'<tr><td>{label}</td><td>2880</td><td>{v["CL"]:.9f}</td><td>{v["CD_inviscid"]:.9f}</td></tr>'
                   for label, v in coefficients.items())
    pictures = ''.join(f'<h2>{title}</h2><img src="{name}.png" alt="{title}">'
                       for name, title in [('pressure_top_bottom', 'Upper and lower pressure'),
                                           ('chordwise_cp', 'Chordwise pressure'),
                                           ('delta_cp', 'Pressure difference'),
                                           ('spanwise_loading', 'Spanwise loading')])
    html = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>WingCAD — matched Weber benchmark</title>
<style>body{{font:17px system-ui;max-width:1200px;margin:35px auto;padding:0 20px;color:#172b40}}img{{width:100%}}table{{border-collapse:collapse;width:100%}}td,th{{padding:12px;border-bottom:1px solid #ccc;text-align:left}}.note{{background:#e7f3ee;padding:20px}}</style>
<h1>Weber wing: matched WingCAD / FLOWPanel comparison</h1>
<p>RAE101 · span 2.4892 m · chord 0.49784 m · sweep 45° · no taper, twist or dihedral · 30 m/s · 4.2° · 1.225 kg/m³.</p>
<table><tr><th>Case</th><th>Panels</th><th>CL</th><th>CD inviscid</th></tr>{rows}<tr><td>Experimental</td><td>—</td><td>0.238</td><td>0.005</td></tr></table>
<p class="note">WingCAD relative to tutorial: CL {differences['CL_percent']:+.8f}%; CD {differences['CD_inviscid_percent']:+.8f}%.<br>
Maximum node difference: {differences['max_vertex_difference_m']:.3e} m. Maximum raw panel Cp difference: {differences['max_abs_Cp_difference']:.3e}.</p>
<p>The WingCAD BRep is built independently from the original airfoil table with profile RAE101F.
Its interpolating curves pass through the tutorial stations; mesh nodes are projected onto this BRep.
Both calculations use the same structured connectivity, open tips, direct vortex-ring formulation,
rigid wake, offsets and FLOWPanel version. No reference pressure or force is used as solver input.</p>
<p>This verifies reproduction of the tutorial's discrete problem through WingCAD, not independent physical validation
or mesh convergence. The continuous CAD interpolant between mesh stations is not claimed identical to the original
FITPACK curve. Experimental discrepancies of the tutorial remain. The older unstructured Gmsh comparison is preserved separately.</p>
<p>Plots use the tutorial's nearest span column and mean of each triangle pair, with no additional smoothing.
Raw per-panel differences are checked before this reduction. Span loads use the tutorial's center-spacing convention;
global coefficients are verified from the full panel forces. The two numerical curves overlap.</p>
<p><a href="comparison.json">Numerical audit</a> · <a href="pressure_sections.csv">Pressure CSV</a> ·
<a href="spanwise_loading.csv">Span loads CSV</a> ·
<a href="https://flow.byu.edu/FLOWPanel.jl/stable/examples/sweptwing-4p2aoa/">Original tutorial</a></p>{pictures}</html>'''
    (output/'report.html').write_text(html, encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
