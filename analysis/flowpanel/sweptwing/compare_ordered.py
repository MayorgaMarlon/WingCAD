"""Evaluate predeclared engineering mesh-convergence criteria on independent CAD meshes."""
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
from matplotlib.collections import PolyCollection

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from analysis.flowpanel.sweptwing.compare import read_vtk, section, B, C, Q, L, D


def sample_panels(triangles, cp, x, eta):
    """Locate fixed evaluation points inside projected triangles; keep raw Cp."""
    result=np.full(x.shape,np.nan)
    for triangle,value in zip(triangles,cp):
        t=np.column_stack(((triangle[:,0]-triangle[:,1])/C,2*triangle[:,1]/B))
        mask=(x>=t[:,0].min()-1e-12)&(x<=t[:,0].max()+1e-12)&(eta>=t[:,1].min()-1e-12)&(eta<=t[:,1].max()+1e-12)
        if not mask.any():continue
        a,b=t[1]-t[0],t[2]-t[0]
        determinant=a[0]*b[1]-a[1]*b[0]
        assert abs(determinant)>1e-16
        dx,dy=x[mask]-t[0,0],eta[mask]-t[0,1]
        u=(dx*b[1]-dy*b[0])/determinant;v=(a[0]*dy-a[1]*dx)/determinant
        inside=(u>=-1e-10)&(v>=-1e-10)&(u+v<=1+1e-10)
        indices=np.flatnonzero(mask)[inside]
        result.flat[indices]=value
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study',type=Path,default=ROOT/'exports/flowpanel/weber/ordered_ls')
    args=parser.parse_args(); study=args.study.resolve()
    criteria=json.loads((study/'criteria.json').read_text())
    folders=sorted((p for p in study.iterdir() if (p/'results/coefficients.toml').exists()),
                   key=lambda p:tomllib.loads((p/'case.toml').read_text())['panels'])
    assert len(folders)>=3
    configs={p.name:tomllib.loads((p/'results/coefficients.toml').read_text()) for p in folders}
    assert len({v['source_sha256'] for v in configs.values()})==1
    datasets={}; sampled={}
    x,eta=np.meshgrid(np.linspace(.01,.99,121),np.linspace(.05,.95,25))
    for name, config in configs.items():
        assert 0.05 < config['CL'] < .5 and 0 < config['CD_inviscid'] < .1, 'Nonphysical result; inspect wake sign'
        assert config['wake_segments']==2*config['span_intervals']
        assert config['maximum_sampled_node_CAD_distance_mm'] < .001
        if config.get('connected_root',False):
            full=read_vtk(study/name/'results/wing_C.vtk')
            positive=full[0][:,:,1].mean(axis=1)>0
            halves=[tuple(v[mask] for v in full) for mask in (~positive,positive)]
        else:
            halves=[read_vtk(study/name/'results'/f'wing_{side}.vtk') for side in ('L','R')]
        datasets[name]=tuple(np.concatenate([h[i] for h in halves]) for i in range(3))
        tri,cp,force=datasets[name]
        worst=tri[int(np.argmin(cp))].mean(axis=0)
        config['Cp_min_location_x_c']=float((worst[0]-abs(worst[1]))/C)
        config['Cp_min_location_abs_eta']=float(2*abs(worst[1])/B)
        extreme=cp < -10
        config['panels_Cp_below_minus_10']=int(extreme.sum())
        config['extreme_panel_CD_contribution']=float(force[extreme].sum(axis=0)@D/(Q*B*C))
        assert np.isclose(force.sum(axis=0)@L/(Q*B*C),config['CL'],rtol=1e-7)
        assert np.isclose(force.sum(axis=0)@D/(Q*B*C),config['CD_inviscid'],rtol=1e-7)
        # Common-domain evaluation of original piecewise-constant panel Cp.
        centers=halves[1][0].mean(axis=1); values=[]
        for upper in (True,False):
            mask=(centers[:,2]>=0)==upper
            values.append(sample_panels(halves[1][0][mask],halves[1][1][mask],x,eta))
        sampled[name]=np.array(values)
        assert np.isfinite(sampled[name]).all(), 'Sampling outside common mesh coverage'
    pairs=[]; names=list(configs)
    for old,new in zip(names,names[1:]):
        delta=sampled[new]-sampled[old]
        metrics=dict(CL_relative_percent=100*abs(configs[new]['CL']/configs[old]['CL']-1),
                     CD_relative_percent=100*abs(configs[new]['CD_inviscid']/configs[old]['CD_inviscid']-1),
                     Cp_rms=float(np.sqrt(np.mean(delta**2))),Cp_p95=float(np.quantile(abs(delta),.95)))
        pairs.append(dict(old=old,new=new,metrics=metrics,passed=all(value<=criteria[key] for key,value in metrics.items())))
    count=criteria['required_successive_passing_pairs']
    passed=len(pairs)>=count and all(p['passed'] for p in pairs[-count:])
    final_case=configs[names[-1]]
    extreme_drag_percent=100*final_case['extreme_panel_CD_contribution']/final_case['CD_inviscid']
    spacing=final_case.get('spacing','cosine')
    contour_metric=final_case.get('contour_metric','chord')
    reconstruction=final_case.get('pressure_reconstruction','legacy_flowpanel')
    reconstruction_note=('Original FLOWPanel pressure and force corrections are retained.'
                         if reconstruction=='legacy_flowpanel' else
                         'Wake-crossing gradient stencils are excluded. Only actual paired TE panels receive the Kutta pressure correction; forces use that same Cp without another index-based correction.')
    experimental_note=('<p><strong>Experimental quadratic reconstruction, rejected for this wing; not enabled in the simulator.</strong></p>'
                       if final_case.get('gradient_polynomial_order',1)==2 else '')
    if final_case.get('experimental_reconstruction') and not experimental_note:
        experimental_note='<p><strong>Experimental pressure reconstruction; not enabled in the simulator. Consult the unchanged acceptance checks below.</strong></p>'
    refinement_ratios=[(configs[b]['contour_intervals']/configs[a]['contour_intervals'],
                        configs[b]['span_intervals']/configs[a]['span_intervals']) for a,b in zip(names,names[1:])]
    ratio_note=('Interval-count refinement ratios are constant in both directions.'
                if np.allclose(refinement_ratios,refinement_ratios[0])
                else 'Refinement ratios vary; small adjacent changes alone can be misleading.')
    output=study/'comparison';output.mkdir(exist_ok=True)
    summary=dict(criteria=criteria,cases=configs,pairs=pairs,engineering_convergence_passed=passed,
                 full_surface_pointwise_convergence_claimed=False)
    (output/'convergence.json').write_text(json.dumps(summary,indent=2))
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    reference=tomllib.loads((ROOT/'exports/flowpanel/weber/reference/coefficients.toml').read_text())
    for ax,key in zip(axes,('CL','CD_inviscid')):
        ax.plot([v['panels'] for v in configs.values()],[v[key] for v in configs.values()],'o-',label='Independent WingCAD CAD grid')
        ax.axhline(reference[key],color='gray',ls='--',label='FLOWPanel tutorial (finite mesh)')
        ax.set(xlabel='Panels',ylabel=key);ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(output/'coefficients.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True,sharey=True)
    records=[]
    for ax,e in zip(axes.flat,(.041,.163,.245,.510)):
        for index,(name,(tri,cp,_)) in enumerate(datasets.items()):
            for side,points in enumerate(section(tri,cp,e)):
                ax.plot(points[:,0],points[:,1],lw=1,color=f'C{index}',label=name if side==0 else None)
                records.extend((name,e,side,a,v) for a,v in points)
        ax.set(title=f'2y/b={e}',xlabel='x/c',ylabel='Cp');ax.grid(alpha=.2)
    axes[0,0].set_ylim(max(1,max(r[-1] for r in records)+.05),min(-1,min(r[-1] for r in records)-.05))
    axes[0,0].legend(fontsize=8)
    fig.tight_layout();fig.savefig(output/'pressure_cuts.png',dpi=180);plt.close(fig)
    with (output/'pressure_cuts.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(('level','eta','side','x/c','Cp'));w.writerows(records)
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,name in zip(axes,(names[0],names[-1])):
        tri,_,_=datasets[name]
        upper=(tri[:,:,2].mean(axis=1)>0)&(tri[:,:,1].mean(axis=1)>0)
        vertices=tri[upper][:,:,[0,1]].copy()
        vertices[:,:,0]=(vertices[:,:,0]-vertices[:,:,1])/C
        vertices[:,:,1]*=2/B
        ax.add_collection(PolyCollection(vertices,facecolors='none',edgecolors='#357ba6',linewidths=.25))
        for e in np.linspace(.1,.9,5):ax.arrow(1,e,.17,0,width=.003,color='#ca6334',length_includes_head=True)
        ax.set(xlim=(-.03,1.22),ylim=(0,1),xlabel='Local x/c',ylabel='2y/b',title=f'{name}: upper mesh and wake projection')
    fig.tight_layout();fig.savefig(output/'mesh_distribution.png',dpi=180);plt.close(fig)
    rows=''.join(f'<tr><td>{name}</td><td>{c["panels"]}</td><td>{c["CL"]:.7f}</td><td>{c["CD_inviscid"]:.7f}</td><td>{c["Cp_min"]:.3g}</td><td>{c["panels_Cp_below_minus_10"]}</td></tr>' for name,c in configs.items())
    checks=''.join(f'<tr><td>{p["old"]} → {p["new"]}</td>'+''.join(f'<td>{v:.5g}</td>' for v in p['metrics'].values())+f'<td>{p["passed"]}</td></tr>' for p in pairs)
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>WingCAD mesh convergence</title>
<style>body{{font:17px system-ui;max-width:1200px;margin:35px auto;color:#172b40}}td,th{{padding:12px;border-bottom:1px solid #ccc;text-align:left}}img{{width:100%}}table{{border-collapse:collapse;width:100%}}</style>
<h1>Independent CAD mesh: convergence assessment</h1>
{experimental_note}
<p>Engineering criteria passed: <strong>{passed}</strong>. Same WingCAD RAE101 BRep, dimensions and conditions;
{spacing} spacing; contour coordinate: {contour_metric}. No reference nodes or profile interpolant used.</p>
<p><strong>Not a full convergence claim.</strong> {ratio_note}
In the finest mesh, panels with Cp below -10 contribute
{extreme_drag_percent:.2f}% of the net inviscid CD (signed). Tip pressures remain unresolved;
small adjacent coefficient changes do not establish asymptotic accuracy.</p>
<table><tr><th>Mesh</th><th>Panels</th><th>CL</th><th>CD inviscid</th><th>Raw Cp minimum</th><th>Panels Cp &lt; −10</th></tr>{rows}</table>
<h2>Predeclared checks</h2><p>Two successive refinements must pass CL ≤1%, CD ≤5%, Cp RMS ≤0.02 and Cp 95th-percentile difference ≤0.05.
Cp uses the raw constant value of the triangle containing each evaluation point on the fixed interior domain x/c=0.01…0.99, |2y/b|=0.05…0.95.
Tip, root and edge singular regions are excluded from this local criterion; this is not a claim of pointwise convergence there.</p>
<table><tr><th>Refinement</th><th>CL change %</th><th>CD change %</th><th>Cp RMS</th><th>Cp p95</th><th>Pass</th></tr>{checks}</table>
<p>Wake segments are paired from actual CAD mesh connectivity with FLOWPanel's reverse boundary orientation,
one wake per upper/lower TE edge pair, directions aligned with freestream.
The original unstructured results remain preserved; this changes the panel distribution,
not the CAD. Agreement with experimental or reference coefficients is not an acceptance criterion.</p>
<p>The connected case shares root nodes, avoiding an artificial open boundary between half-wings.
Pressure reconstruction: {reconstruction}. Adaptive stencil: {final_case.get('adaptive_stencil',False)}.
{reconstruction_note} Raw singular tip values are retained above.</p>
<p><a href="convergence.json">Full numerical audit</a> · <a href="pressure_cuts.csv">Raw pressure cuts</a></p>
<img src="mesh_distribution.png" alt="Mesh distribution and projected wake"><img src="coefficients.png" alt="Coefficient refinement"><img src="pressure_cuts.png" alt="Unsmoothed pressure cuts"></html>'''
    (output/'report.html').write_text(html,encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
