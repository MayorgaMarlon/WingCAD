"""Bundle completed convergence diagnostics into a portable, reviewable report."""
import json
from pathlib import Path
import shutil
import tomllib

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'exports/flowpanel/weber'
DEST=Path(__file__).resolve().parent/'results'


def main():
    target=DEST/'directional';target.mkdir(parents=True,exist_ok=True)
    for source in (SOURCE/'directional_comparison').iterdir():
        if source.is_file():
            shutil.copyfile(source,target/('matrix_report.html' if source.name=='report.html' else source.name))
    rows=[]
    matrix=json.loads((SOURCE/'directional_comparison/directional.json').read_text())
    for label,key in (('Mirrored, cosine','cosine'),('Mirrored, bounded','bounded')):
        s=matrix['studies'][key]
        rows.append((label,s['cases']['c54_s36'],[p for p in s['pairs'] if p['direction']=='both'][-1],s['fixed_ratio_pressure_checks_passed']))
    for label,name in (('More chord panels','chord_resolved'),('CAD arc-length sampling','arc_resolved'),
                       ('Quadratic gradient: rejected','chord_resolved_quadratic'),
                       ('Adaptive quadratic: rejected','chord_resolved_adaptive')):
        source=SOURCE/name/'comparison';folder=DEST/name
        folder.mkdir(parents=True,exist_ok=True)
        for path in source.iterdir():
            if path.is_file():shutil.copyfile(path,folder/path.name)
        summary=json.loads((source/'convergence.json').read_text())
        rows.append((label,summary['cases']['fine'],summary['pairs'][-1],summary['engineering_convergence_passed']))
    sphere=tomllib.loads((SOURCE/'sphere_validation_refined.toml').read_text())
    for name in ('sphere_validation.toml','sphere_validation_refined.toml'):
        shutil.copyfile(SOURCE/name,target/name)
    cells=''
    for label,c,p,passed in rows:
        m=p['metrics']
        cells+=f'<tr><td>{label}</td><td>{c["panels"]}</td><td>{c["CL"]:.7f}</td><td>{c["CD_inviscid"]:.7f}</td><td>{m["CL_relative_percent"]:.3f}</td><td>{m["CD_relative_percent"]:.3f}</td><td>{m["Cp_rms"]:.5f}</td><td>{passed}</td></tr>'
    sphere_rows=''.join(f'<tr><td>{c["panels"]}</td><td>{c["Cp_RMS_error"]:.6f}</td><td>{c["Cp_max_error"]:.6f}</td></tr>' for c in sphere['cases'])
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>WingCAD convergence investigation</title>
<style>body{{font:17px system-ui;max-width:1250px;margin:35px auto;color:#172b40}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}table{{border-collapse:collapse;width:100%}}img{{width:100%}}.notice{{background:#fff1d5;padding:18px}}</style>
<h1>WingCAD: convergence investigation</h1>
<p class="notice"><strong>Wing pressure convergence is not demonstrated.</strong>
The fixed-ratio studies do not pass all predeclared criteria on two consecutive refinements.
No pressure clipping, smoothing or reference-coefficient fitting was used.</p>
<p>28 completed wing runs: two nine-case directional matrices, one symmetry control,
three closed-tip diagnostics, three chord-resolved cases and three CAD arc-length cases.
All retain the same RAE101 CAD and flight conditions. Closed-tip cases are explicitly separate fluid boundaries.
Six additional pressure reconstructions reuse the same solved circulation; they are not new flow solves.</p>
<h2>Finest case in each open-tip study</h2>
<p>Changes compare the final two levels. Acceptance requires two successive passes:
CL ≤1%, CD ≤5%, interior Cp RMS ≤0.02 and Cp p95 ≤0.05.</p>
<table><tr><th>Study</th><th>Panels</th><th>CL</th><th>CD pressure</th><th>ΔCL %</th><th>ΔCD %</th><th>Cp RMS</th><th>Two passes?</th></tr>{cells}</table>
<h2>What the checks establish</h2>
<ul><li>Mirrored triangulation removes the previous left/right mesh asymmetry.</li>
<li>Actual trailing-edge pairs form a continuous rigid wake; wake-force diagnostics are less sensitive than pressure forces.</li>
<li>Span refinement and tip pressure remain sensitive. Closed caps remove extreme upper/lower-surface values but introduce sharp-cap extrema and do not fix pressure-drag convergence.</li>
<li>Higher chord resolution and true CAD arc-length sampling were tested independently; neither is presented as a complete fix.</li></ul>
<p>Quadratic pressure reconstruction was also tested with fixed and geometry-conditioned neighbourhoods.
Both variants produced worse raw pressure peaks and drag sensitivity, so they are rejected for this wing and are not enabled in the simulator.</p>
<p><a href="matrix_report.html">Directional matrices, wake forces and closed tips</a> ·
<a href="../chord_resolved/report.html">6144 → 13824 → 31104 panels</a> ·
<a href="../arc_resolved/report.html">CAD arc-length study</a></p>
<p><a href="../chord_resolved_quadratic/report.html">Rejected quadratic reconstruction</a> ·
<a href="../chord_resolved_adaptive/report.html">Rejected adaptive quadratic reconstruction</a></p>
<img src="directional.png" alt="Pressure versus wake force sensitivity">
<h2>Analytic pressure validation: sphere</h2>
<p>The complete solver/velocity/pressure chain is checked against Cp=1−2.25 sin²θ.
The original 1280-panel run missed the fixed RMS limit 0.05; the refined run retains that limit.
Refined validation passed: <strong>{sphere['passed']}</strong>. This smooth-surface check does not validate sharp wing edges.</p>
<table><tr><th>Panels</th><th>Cp RMS error</th><th>Cp maximum error</th></tr>{sphere_rows}</table>
<p><a href="sphere_validation_refined.toml">Analytic validation data</a> ·
<a href="sphere_validation.toml">Initial validation, preserved</a> ·
<a href="https://farside.ph.utexas.edu/teaching/336L/Fluidhtml/node102.html">Sphere potential-flow solution</a></p>
<p>Ten Python numerical tests cover gradients, wake discontinuities, reflection, closed-tip connectivity,
bounded spacing and analytical wake forces. No graphical application was launched for testing.</p></html>'''
    (target/'report.html').write_text(html,encoding='utf-8')
    print(target/'report.html')


if __name__=='__main__':main()
