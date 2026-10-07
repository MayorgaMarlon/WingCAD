"""Report an independent, fixed-CAD mesh refinement study without Qt or VTK."""
import csv
import json
import tomllib
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from analysis.flowpanel.sweptwing.compare import read_vtk, section, loading, B, C, Q, D, L, DATA, OUT

STUDY = OUT/'independent'
LEVELS = ('coarse', 'medium', 'fine')


def write_csv(path, header, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream); writer.writerow(header); writer.writerows(rows)


def main():
    output = STUDY/'comparison'; output.mkdir(exist_ok=True)
    refparts = [read_vtk(OUT/'reference'/f'reference_{s}.vtk') for s in ('L', 'R')]
    datasets = {'FLOWPanel reference': tuple(np.concatenate([part[i] for part in refparts]) for i in range(3))}
    configs = {'FLOWPanel reference': tomllib.loads((OUT/'reference/coefficients.toml').read_text())}
    audit = json.loads((STUDY/'geometry_audit.json').read_text())
    for level in LEVELS:
        name = 'WingCAD '+level
        datasets[name] = read_vtk(STUDY/level/'results/manta.vtk')
        configs[name] = tomllib.loads((STUDY/level/'results/coefficients.toml').read_text())
        assert configs[name]['source_sha256'] == audit['source_sha256']
        assert configs[name]['step_sha256'] == audit['step_sha256']
        assert configs[name]['solver_formulation'] == 'direct_open_surface'
        assert not configs[name]['tip_caps']
    assert len({configs['WingCAD '+s]['mesh_sha256'] for s in LEVELS}) == 3
    for name, config in configs.items():
        for key, value in dict(speed_mps=30., aoa_deg=4.2, density_kg_m3=1.225,
                               bref_m=B, sref_m2=B*C).items():
            assert np.isclose(config[key], value), (name, key)
        assert config['flowpanel_version'] == configs['FLOWPanel reference']['flowpanel_version']
        tri, cp, force = datasets[name]
        assert len(tri) == config['panels']
        assert np.isclose(force.sum(axis=0)@L/(Q*B*C), config['CL'], rtol=1e-7)
        assert np.isclose(force.sum(axis=0)@D/(Q*B*C), config['CD_inviscid'], rtol=1e-7)
    changes = {}
    for old, new in zip(LEVELS, LEVELS[1:]):
        changes[f'{old}_to_{new}'] = {k: 100*(configs['WingCAD '+new][k]/configs['WingCAD '+old][k]-1)
                                     for k in ('CL', 'CD_inviscid')}
    difference = {k: 100*(configs['WingCAD fine'][k]/configs['FLOWPanel reference'][k]-1)
                  for k in ('CL', 'CD_inviscid')}
    colors = dict(zip(datasets, ('#1e65a4', '#969696', '#d5a213', '#d04b22')))
    exp = json.loads((DATA/'experimental.json').read_text())
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, key, measured in zip(axes, ('CL', 'CD_inviscid'), (.238, .005)):
        ax.plot([configs['WingCAD '+s]['panels'] for s in LEVELS],
                [configs['WingCAD '+s][key] for s in LEVELS], 'o-', color='#d04b22', label='WingCAD independent mesh')
        ax.axhline(configs['FLOWPanel reference'][key], color='#1e65a4', label='FLOWPanel tutorial (2,880 panels)')
        ax.axhline(measured, color='black', ls=':', label='Experimental')
        ax.set(xlabel='Number of triangles', ylabel=key); ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.suptitle('Fixed WingCAD geometry — independent Gmsh refinement')
    fig.tight_layout(); fig.savefig(output/'refinement.png', dpi=180); plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, sharey=True)
    records = []
    for ax, eta in zip(axes.flat, (.041, .163, .245, .510)):
        for name, (tri, cp, _) in datasets.items():
            for side, points in enumerate(section(tri, cp, eta)):
                ax.plot(points[:, 0], points[:, 1], color=colors[name], lw=1,
                        alpha=.8, label=name if side == 0 else None)
                records.extend((name, eta, side, x, value) for x, value in points)
        key = min(exp['Cp'], key=lambda k: abs(float(k)-eta))
        for side, xkey in enumerate(('weber_xoc_up', 'weber_xoc_lo')):
            ax.scatter(exp[xkey], [np.nan if v is None else v for v in exp['Cp'][key][side]],
                       s=15, color='black', label='Experimental' if side == 0 else None, zorder=5)
        ax.set(title=f'2y/b = {eta}', xlabel='x/c', ylabel='Cp', xlim=(-.02, 1.02))
        ax.grid(alpha=.2)
    values = [r[-1] for r in records]
    axes[0, 0].set_ylim(max(1, max(values)+.05), min(-.9, min(values)-.05))
    axes[0, 0].legend(fontsize=7)
    fig.suptitle('Raw plane cuts — no pressure smoothing, same extraction for every mesh')
    fig.tight_layout(); fig.savefig(output/'chordwise_cp.png', dpi=180); plt.close(fig)
    write_csv(output/'pressure_sections.csv', ('case', '2y/b', 'side_0_upper', 'x/c', 'Cp'), records)

    edges = np.linspace(-B/2, B/2, 31); edges[0] -= 1e-9; edges[-1] += 1e-9
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5)); records = []
    eta = (edges[:-1]+edges[1:])/B
    for name, (tri, cp, force) in datasets.items():
        loads = loading(tri, force, edges)  # Also checks conservation of force.
        for i, ax in enumerate(axes):
            ax.plot(eta, loads[:, i], '.-', lw=1, color=colors[name], label=name)
        records.extend((name, e, cl, cd) for e, (cl, cd) in zip(eta, loads))
    for ax, key, title in zip(axes, ('cls_web', 'cds_web'), ('Sectional lift cl', 'Sectional drag cd')):
        ys, values = np.array(exp['y2b_web']), np.array(exp[key])
        ax.scatter(np.r_[-ys[::-1], ys], np.r_[values[::-1], values], s=16, c='black', label='Experimental')
        ax.set(xlabel='2y/b', ylabel=title); ax.grid(alpha=.2); ax.legend(fontsize=7)
    fig.suptitle('Common span bands — conservative area-weighted forces')
    fig.tight_layout(); fig.savefig(output/'spanwise_loading.png', dpi=180); plt.close(fig)
    write_csv(output/'spanwise_loading.csv', ('case', '2y/b', 'cl', 'cd'), records)

    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    for row, name in enumerate(('FLOWPanel reference', 'WingCAD fine')):
        tri, cp, _ = datasets[name]
        for col, upper in enumerate((True, False)):
            mask = (tri[:, :, 2].mean(axis=1) > 0) == upper
            vertices = tri[mask][:, :, [1, 0]].copy(); vertices[:, :, 1] *= -1
            pc = PolyCollection(vertices, array=cp[mask], cmap='coolwarm', clim=(-.5, .5), edgecolors='none')
            ax = axes[row, col]; ax.add_collection(pc); ax.autoscale_view(); ax.set_aspect('equal')
            ax.set(title=name+(' — upper' if upper else ' — lower'), xlabel='y (m)', ylabel='−x (m)')
            fig.colorbar(pc, ax=ax, label='Cp (color range ±0.5)', shrink=.6)
    fig.tight_layout(); fig.savefig(output/'pressure_top_bottom.png', dpi=180); plt.close(fig)

    profile = np.loadtxt(STUDY/'profile_distances.csv', delimiter=',', skiprows=1)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for side in (0, 1):
        rows = profile[profile[:, 0] == side]
        axes[0].plot(rows[:, 1], rows[:, 2], color='#1e65a4', label='Continuous reference' if side == 0 else None)
        axes[0].plot(rows[:, 3], rows[:, 4], color='#d04b22', ls='--', label='Nearest points on WingCAD section' if side == 0 else None)
        axes[1].plot(rows[:, 1], rows[:, 5], label='Upper' if side == 0 else 'Lower')
    axes[0].set(xlabel='x/c', ylabel='z/c'); axes[0].set_aspect('equal', adjustable='datalim')
    axes[1].set(xlabel='Reference x/c', ylabel='Distance to CAD section (mm)')
    for ax in axes: ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(output/'profile_geometry.png', dpi=180); plt.close(fig)
    summary = dict(geometry_audit=audit, cases=configs, adjacent_mesh_changes_percent=changes,
                   fine_vs_reference_percent=difference,
                   convergence_demonstrated=False,
                   interpretation='Changes on fixed CAD measure mesh sensitivity, not an error bound. Residual is not solely geometry error.')
    (output/'comparison.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    rows = ''.join(f'<tr><td>{name}</td><td>{v["panels"]}</td><td>{v["CL"]:.6f}</td><td>{v["CD_inviscid"]:.6f}</td></tr>' for name, v in configs.items())
    metrics = ''.join(f'<li>{step}: CL {v["CL"]:+.2f}%, CD {v["CD_inviscid"]:+.2f}%.</li>' for step, v in changes.items())
    images = ''.join(f'<h2>{title}</h2><img src="{file}.png" alt="{title}">' for file, title in
                     [('refinement', 'Mesh sensitivity'), ('profile_geometry', 'Independent geometry audit'),
                      ('pressure_top_bottom', 'Upper and lower pressure'), ('chordwise_cp', 'Chordwise pressure'),
                      ('spanwise_loading', 'Spanwise loads')])
    html = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>WingCAD independent mesh study</title>
<style>body{{font:17px system-ui;max-width:1200px;margin:35px auto;padding:0 20px;color:#172b40}}img{{width:100%}}table{{border-collapse:collapse;width:100%}}td,th{{padding:12px;border-bottom:1px solid #ccc;text-align:left}}.note{{background:#fff1d8;padding:20px}}</style>
<h1>Weber wing: independent WingCAD mesh refinement</h1>
<p>RAE101 · span 2.4892 m · chord 0.49784 m · sweep 45° · 30 m/s · 4.2° · 1.225 kg/m³.</p>
<p>WingCAD example 08, standard RAE101 interpolation. One fixed STEP for all three meshes.
No reference mesh nodes or topology are used to generate these meshes. The matched example 09 is not used.</p>
<table><tr><th>Case</th><th>Panels</th><th>CL</th><th>CD inviscid</th></tr>{rows}<tr><td>Experimental</td><td>—</td><td>0.238</td><td>0.005</td></tr></table>
<p class="note">Fine WingCAD versus tutorial: CL {difference['CL']:+.2f}%, CD {difference['CD_inviscid']:+.2f}%.
Convergence has not been established; these differences are not a geometry-only error estimate.</p>
<p>Successive changes on the same CAD:</p><ul>{metrics}</ul>
<p>Mesh size limits decrease by a factor of 1.5 at each step. CAD/source hashes match;
mesh hashes differ. Tip caps are removed consistently; all remaining openings are at the tips.
Parent meshes have positive signed volume and consistent panel orientation. All fields are finite,
and integrated forces reproduce saved CL/CD. FLOWPanel reports a winding-number warning for the open surface;
this warning is retained in each solver log, not treated as proof of an inverted mesh.</p>
<p>Independent geometry measurement: maximum one-way distance to the CAD section
{audit['max_reference_to_CAD_distance_mm']:.4f} mm, RMS {audit['rms_reference_to_CAD_distance_mm']:.4f} mm
over {audit['samples']} points at y = {audit['section_y_mm']} mm. This is a sampled sectional distance,
not a global Hausdorff bound and not an aerodynamic error estimate.</p>
<p>Both solvers use direct vortex-ring panels and the same rigid wake/conditions. The tutorial has two
structured half-wing bodies; this adapter uses a connected unstructured mesh. The remaining difference includes
CAD interpolation, triangulation, gradient reconstruction, body partition and finite resolution of both solutions.
More refinement alone does not isolate these effects. No coefficients or nodes were tuned to improve agreement.</p>
<p>Pressure cuts use identical plane intersections for every case, without smoothing; they differ from the
tutorial's nearest-column plotting procedure. Span forces are conservatively integrated into the same 30 bands.
Colors are clipped to ±0.5, but numerical pressure data retain the full range.</p>
<p><a href="comparison.json">Full audit JSON</a> · <a href="pressure_sections.csv">Pressure CSV</a> ·
<a href="spanwise_loading.csv">Span loads CSV</a> ·
<a href="https://flow.byu.edu/FLOWPanel.jl/stable/examples/sweptwing-4p2aoa/">Reference tutorial</a></p>{images}</html>'''
    (output/'report.html').write_text(html, encoding='utf-8')
    print(json.dumps(dict(changes=changes, fine_vs_reference=difference,
                          coefficients={k: {q: v[q] for q in ('panels', 'CL', 'CD_inviscid')} for k, v in configs.items()}), indent=2))


if __name__ == '__main__':
    main()
