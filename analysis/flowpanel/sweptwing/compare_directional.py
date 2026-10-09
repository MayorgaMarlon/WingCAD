"""Separate chord/span sensitivity from pressure and rigid-wake diagnostics."""
import argparse
import csv
import json
from pathlib import Path
import sys
import tomllib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from analysis.flowpanel.sweptwing.reconstruct_pressure import load_fields
from analysis.flowpanel.sweptwing.mesh_quality import quality,reflection_pairs
from analysis.flowpanel.sweptwing.compare_ordered import sample_panels
from analysis.flowpanel.sweptwing.compare import section
from analysis.flowpanel.sweptwing.wake_forces import from_solution


def assess(study):
    cases={};samples={};datasets={}
    x,eta=np.meshgrid(np.linspace(.01,.99,121),np.linspace(.05,.95,25))
    for nc in (24,36,54):
        for ns in (16,24,36):
            name=f'c{nc}_s{ns}';folder=study/name
            config=tomllib.loads((folder/'results/coefficients.toml').read_text())
            nodes,cells,fields=load_fields(folder/'results/wing_C.vtk')
            tri=nodes[cells];centers=tri.mean(axis=1)
            audit=quality(nodes,cells);mirror=reflection_pairs(nodes,cells)
            assert np.all(mirror>=0)
            audit['Cp_symmetry_max']=float(np.max(abs(fields['Cp']-fields['Cp'][mirror])))
            assert audit['Cp_symmetry_max']<1e-7
            values=[]
            for sign in (-1,1):
                mask=(centers[:,1]>0)&(centers[:,2]*sign>0)
                values.append(sample_panels(tri[mask],fields['Cp'][mask],x,eta))
            samples[name]=np.array(values);assert np.isfinite(samples[name]).all()
            wake=from_solution(nodes,cells,fields,config)
            worst=int(np.argmin(fields['Cp']))
            audit['Cp_min_location'] = centers[worst].tolist()
            audit['principal_speed_at_Cp_min']=float(np.linalg.norm(fields['U'][worst]-fields['Ugradmu'][worst]))
            audit['gradient_speed_at_Cp_min']=float(np.linalg.norm(fields['Ugradmu'][worst]))
            # Preserve contribution of the tip strip to the full force sum.
            direction=np.array([np.cos(np.deg2rad(config['aoa_deg'])),0,np.sin(np.deg2rad(config['aoa_deg']))])
            qS=.5*config['density_kg_m3']*config['speed_mps']**2*config['sref_m2']
            tip=abs(centers[:,1])>.95*config['bref_m']/2
            audit['tip_5_percent_CD']=float(fields['F'][tip].sum(axis=0)@direction/qS)
            config.update(wake);config['audit']=audit
            cases[name]=config;datasets[name]=(tri,fields['Cp'])
    assert len({c['source_sha256'] for c in cases.values()})==1
    criteria=json.loads((study/'criteria.json').read_text());pairs=[]
    sequences=[('chord',f'span={s}',[f'c{c}_s{s}' for c in (24,36,54)]) for s in (16,24,36)]
    sequences += [('span',f'chord={c}',[f'c{c}_s{s}' for s in (16,24,36)]) for c in (24,36,54)]
    sequences += [('both','ratio=1.5',['c24_s16','c36_s24','c54_s36'])]
    for direction,fixed,names in sequences:
        for old,new in zip(names,names[1:]):
            a,b=cases[old],cases[new];delta=samples[new]-samples[old]
            metrics=dict(CL_relative_percent=100*abs(b['CL']/a['CL']-1),
                         CD_relative_percent=100*abs(b['CD_inviscid']/a['CD_inviscid']-1),
                         Cp_rms=float(np.sqrt(np.mean(delta**2))),Cp_p95=float(np.quantile(abs(delta),.95)))
            pairs.append(dict(direction=direction,fixed=fixed,old=old,new=new,metrics=metrics,
                              passed=all(v<=criteria[k] for k,v in metrics.items()),
                              wake_CL_change_percent=100*abs(b['CL_wake']/a['CL_wake']-1),
                              wake_CD_change_percent=100*abs(b['CD_trefftz']/a['CD_trefftz']-1)))
    return dict(cases=cases,pairs=pairs,criteria=criteria,
                fixed_ratio_pressure_checks_passed=all(p['passed'] for p in pairs if p['direction']=='both')) ,datasets


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cosine',type=Path,default=ROOT/'exports/flowpanel/weber/directional')
    parser.add_argument('--bounded',type=Path,default=ROOT/'exports/flowpanel/weber/directional_bounded')
    parser.add_argument('--output',type=Path,default=ROOT/'exports/flowpanel/weber/directional_comparison')
    parser.add_argument('--closed',type=Path,default=ROOT/'exports/flowpanel/weber/closed_tip_diagnostic')
    args=parser.parse_args();output=args.output;output.mkdir(exist_ok=True,parents=True)
    studies={};data={}
    for name,path in (('cosine',args.cosine),('bounded',args.bounded)):
        studies[name],data[name]=assess(path)
    assert len({c['source_sha256'] for s in studies.values() for c in s['cases'].values()})==1
    summary=dict(studies=studies,full_convergence_demonstrated=False,
                 wake_method='Unscaled midpoint Trefftz diagnostic of the prescribed rigid wake; no relaxation')
    closed_rows=''
    closed_results={}
    for name in ('c24_s16','c36_s24','c54_s36'):
        folder=args.closed/name/'results'
        if not (folder/'coefficients.toml').exists():continue
        c=tomllib.loads((folder/'coefficients.toml').read_text())
        nodes,cells,fields=load_fields(folder/'wing_C.vtk');tri=nodes[cells]
        cap=np.ptp(tri[:,:,1],axis=1)<1e-12
        c['Cp_min_wing_surfaces']=float(fields['Cp'][~cap].min())
        c.update(from_solution(nodes,cells,fields,c));closed_results[name]=c
        closed_rows+=f'<tr><td>{name}</td><td>{c["panels"]}</td><td>{c["CL"]:.7f}</td><td>{c["CD_inviscid"]:.7f}</td><td>{c["CD_trefftz"]:.7f}</td><td>{c["Cp_min"]:.3f}</td><td>{c["Cp_min_wing_surfaces"]:.3f}</td><td>{c["normal_velocity_rms_mps"]:.6g}</td></tr>'
    summary['closed_tip_diagnostic']=closed_results
    (output/'directional.json').write_text(json.dumps(summary,indent=2))
    records=[]
    for scheme,study in studies.items():
        for name,c in study['cases'].items():
            records.append([scheme,name,c['panels'],c['CL'],c['CD_inviscid'],c['CL_wake'],c['CD_trefftz'],c['Cp_min'],c['audit']['all']['aspect_max']])
    with (output/'coefficients.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['spacing','case','panels','CL_pressure','CD_pressure','CL_wake','CD_Trefftz','Cp_min','aspect_max']);writer.writerows(records)
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for row,(scheme,study) in enumerate(studies.items()):
        for ns in (16,24,36):
            cases=[study['cases'][f'c{nc}_s{ns}'] for nc in (24,36,54)]
            for col,key in enumerate(('CL','CD_inviscid')):
                line,=axes[row,col].plot([24,36,54],[c[key] for c in cases],'o-',label=f'Pressure; span={ns}')
                wake_key='CL_wake' if col==0 else 'CD_trefftz'
                axes[row,col].plot([24,36,54],[c[wake_key] for c in cases],'--',color=line.get_color(),label=f'Wake; span={ns}')
                axes[row,col].set(title=f'{scheme}: {key}',xlabel='Chord intervals per surface',ylabel=key)
                axes[row,col].grid(alpha=.2)
    for ax in axes.flat:ax.legend(fontsize=7)
    fig.tight_layout();fig.savefig(output/'directional.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,8),sharey=True)
    for ax,eta in zip(axes.flat,(.163,.51,.90,.98)):
        for index,(scheme,study) in enumerate(data.items()):
            for j,name in enumerate(('c24_s16','c36_s24','c54_s36')):
                tri,cp=study[name]
                for side,points in enumerate(section(tri,cp,eta)):
                    ax.plot(points[:,0],points[:,1],color=f'C{3*index+j}',lw=.9,label=f'{scheme} {name}' if side==0 else None)
        ax.set(title=f'2y/b={eta}',xlabel='x/c',ylabel='Cp');ax.grid(alpha=.2)
    axes[0,0].invert_yaxis();axes[0,0].legend(fontsize=7)
    fig.tight_layout();fig.savefig(output/'pressure.png',dpi=160);plt.close(fig)
    rows=''.join('<tr>'+''.join(f'<td>{v:.7g}</td>' if isinstance(v,float) else f'<td>{v}</td>' for v in row)+'</tr>' for row in records)
    checks=''
    for scheme,s in studies.items():
        for p in s['pairs']:
            m=p['metrics']
            checks+=f'<tr><td>{scheme}</td><td>{p["direction"]}: {p["old"]} → {p["new"]}</td><td>{m["CL_relative_percent"]:.3f}</td><td>{m["CD_relative_percent"]:.3f}</td><td>{m["Cp_rms"]:.5f}</td><td>{m["Cp_p95"]:.5f}</td><td>{p["passed"]}</td></tr>'
    (output/'report.html').write_text(f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>WingCAD directional refinement</title>
<style>body{{font:16px system-ui;max-width:1250px;margin:35px auto;color:#172b40}}td,th{{padding:8px;border-bottom:1px solid #ddd;text-align:left}}table{{border-collapse:collapse;width:100%}}img{{width:100%}}</style>
<h1>Independent CAD: directional refinement and wake check</h1>
<p>Same RAE101 CAD, 2.4892 m span, 0.49784 m chord, 45° sweep, 30 m/s, 4.2°, 1.225 kg/m³.
Root connected, tips open, mirrored shortest-diagonal triangulation. No reference nodes or pressure clipping.</p>
<p>Two 3×3 studies separate chord and span refinement. The diagonal sequence uses an exact 1.5 interval-count ratio in both directions.
Bounded spacing uses a fixed smooth map with derivative between 0.1 and 1.9; it is not fitted to the reference.</p>
<p><strong>Full convergence has not been demonstrated.</strong> Pressure acceptance uses the previous fixed thresholds:
CL 1%, CD 5%, interior Cp RMS 0.02, p95 0.05, two consecutive refinements.
The wake result is an independent diagnostic, not a replacement or a rescaling of pressure drag.</p>
<img src="directional.png" alt="Separate directional refinement, pressure versus wake">
<table><tr><th>Spacing</th><th>Case</th><th>Panels</th><th>CL pressure</th><th>CD pressure</th><th>CL wake</th><th>CD Trefftz</th><th>Raw Cp min</th><th>Max aspect</th></tr>{rows}</table>
<h2>Unchanged acceptance checks</h2><table><tr><th>Spacing</th><th>Refinement</th><th>ΔCL %</th><th>ΔCD %</th><th>Cp RMS</th><th>Cp p95</th><th>Pass</th></tr>{checks}</table>
<h2>Raw pressure cuts, including the tip region</h2><img src="pressure.png" alt="Unsmoothed pressure cuts">
<h2>Separate diagnostic: closed CAD tip faces</h2>
<p>Different fluid boundary from the open-tip tutorial, with FLOWPanel's closed least-squares solver.
The raw minimum includes tip caps; the wing-surface minimum is reported separately to localize the peaks, not to remove them.</p>
<table><tr><th>Case</th><th>Panels</th><th>CL pressure</th><th>CD pressure</th><th>CD Trefftz</th><th>Raw Cp min</th><th>Wing surface Cp min</th><th>Normal residual RMS, m/s</th></tr>{closed_rows}</table>
<p><a href="directional.json">All audits and wake comparisons</a> · <a href="coefficients.csv">Coefficient table</a></p>
<p>Trefftz quadrature uses the actual solved circulation and the rigid wake projected normal to freestream;
it was checked against elliptical loading. It does not establish relaxed-wake accuracy.
See <a href="https://mit-lae.github.io/TASOPT.jl/dev/aero/drag/">the impulse and energy formulation</a>.
No empirical circulation shape or lift-based scaling is applied here.</p></html>''',encoding='utf-8')
    for scheme,s in studies.items():
        print(scheme,'fixed-ratio pressure checks:',s['fixed_ratio_pressure_checks_passed'])
        for p in s['pairs']:
            if p['direction']=='both':print(p)


if __name__=='__main__':main()
