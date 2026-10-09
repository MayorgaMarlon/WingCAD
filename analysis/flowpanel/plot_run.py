"""Generate plots from ONE saved Weber run, without reference/experimental data."""
import csv
import hashlib
import json
from pathlib import Path
import sys
import tomllib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from core.flowpanel_workflow import read_case, is_weber_case
from analysis.flowpanel.sweptwing.compare import read_vtk, section, loading, B, C
from analysis.flowpanel.sweptwing.compare_ordered import sample_panels


def generate(folder):
    folder=Path(folder).resolve()
    if not is_weber_case(read_case(folder)):
        raise ValueError('These section plots currently support the isolated Weber wing.')
    source=folder/'results/wing_C.vtk'
    coefficients=folder/'results/coefficients.toml'
    cfg=tomllib.loads(coefficients.read_text(encoding='utf-8'))
    assert np.isclose(cfg['bref_m'],B) and np.isclose(cfg['sref_m2'],B*C)
    tri,cp,forces=read_vtk(source)
    assert len(cp)==cfg['panels']
    alpha=np.deg2rad(cfg['aoa_deg'])
    drag=np.array([np.cos(alpha),0.,np.sin(alpha)]);lift=np.cross(drag,[0,1,0])
    q=.5*cfg['density_kg_m3']*cfg['speed_mps']**2
    for key,direction in [('CL',lift),('CD_inviscid',drag)]:
        assert np.isclose(forces.sum(axis=0)@direction/(q*cfg['sref_m2']),cfg[key],rtol=1e-7,atol=1e-10)
    output=folder/'results/plots';output.mkdir(exist_ok=True)
    def write(name,header,rows):
        with (output/name).open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(header);w.writerows(rows)
    subtitle=f"WingCAD | {cfg['panels']:,} panels | {cfg['speed_mps']:g} m/s | AoA {cfg['aoa_deg']:g} deg"
    records=[]
    fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True,sharey=True)
    for ax,eta in zip(axes.flat,(.041,.163,.245,.510)):
        for surface,points in zip(('Upper surface','Lower surface'),section(tri,cp,eta)):
            assert len(points)>0
            ax.plot(points[:,0],points[:,1],label=surface,lw=1.2)
            records.extend((eta,surface,x,v) for x,v in points)
        ax.set(title=f'2y/b = {eta:g}',xlabel='x/c',ylabel='Cp');ax.grid(alpha=.2)
    axes[0,0].invert_yaxis();axes[0,0].legend()
    fig.suptitle('Chordwise pressure\n'+subtitle)
    fig.tight_layout();fig.savefig(output/'pressure.png',dpi=160);plt.close(fig)
    write('pressure.csv',['eta','surface','x_over_c','Cp'],records)
    fig,axes=plt.subplots(5,2,figsize=(12,16),sharex=True,sharey=True)
    centers=tri.mean(axis=1);x=np.linspace(.001,.999,300);records=[]
    for ax,eta in zip(axes.flat,(0.,.04,.08,.16,.24,.51,.65,.9,.95)):
        values=[]
        for sign in (1,-1):
            mask=(centers[:,1]>0)&(centers[:,2]*sign>0)
            values.append(sample_panels(tri[mask],cp[mask],x,np.full_like(x,max(eta,1e-7))))
        assert np.isfinite(values).all()
        delta=values[0]-values[1]
        ax.plot(x,delta,color='#2379b5',lw=1.2)
        records.extend((eta,a,u,l,u-l) for a,u,l in zip(x,*values))
        ax.set(title=f'2y/b = {eta:g}',xlabel='x/c',ylabel='Cp upper - Cp lower');ax.grid(alpha=.2)
    axes[0,0].invert_yaxis();axes[-1,-1].axis('off')
    fig.suptitle('Pressure difference\n'+subtitle)
    fig.tight_layout();fig.savefig(output/'delta_pressure.png',dpi=150);plt.close(fig)
    write('delta_pressure.csv',['eta','x_over_c','Cp_upper','Cp_lower','delta_Cp'],records)
    edges=np.linspace(-B/2,B/2,31);edges[0]-=1e-9;edges[-1]+=1e-9
    loads=loading(tri,forces,edges,lift=lift,drag=drag,dynamic_pressure=q,chord=C)
    eta=(edges[:-1]+edges[1:])/B
    for j,key in enumerate(('CL','CD_inviscid')):
        assert np.isclose(np.sum(loads[:,j]*np.diff(edges)*C)/cfg['sref_m2'],cfg[key],rtol=1e-7,atol=1e-10)
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for j,(ax,label) in enumerate(zip(axes,('Sectional lift cl','Sectional inviscid drag cd'))):
        ax.plot(eta,loads[:,j],'o-',markersize=3,color='#2379b5')
        ax.set(xlabel='Span position 2y/b',ylabel=label);ax.grid(alpha=.2)
    fig.suptitle('Spanwise loading\n'+subtitle)
    fig.tight_layout();fig.savefig(output/'span_loading.png',dpi=160);plt.close(fig)
    write('span_loading.csv',['y_lower_m','y_upper_m','eta','cl','cd'],
          [(lo,hi,e,a,b) for lo,hi,e,(a,b) in zip(edges[:-1],edges[1:],eta,loads)])
    write('coefficients.csv',['panels','speed_mps','aoa_deg','density_kg_m3','CL','CD_inviscid'],
          [[cfg[k] for k in ('panels','speed_mps','aoa_deg','density_kg_m3','CL','CD_inviscid')]])
    manifest=dict(run=str(folder),title=subtitle,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        coefficients_sha256=hashlib.sha256(coefficients.read_bytes()).hexdigest(),
        reference_data_used=False,experimental_data_used=False,
        method='Raw panel Cp; lines join section samples. Delta Cp uses constant triangle values at common x/c; root sampled at eta=1e-7. Span loads conserve the saved forces. No clipping or smoothing.')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(output,flush=True)
    return output


if __name__=='__main__':generate(Path(sys.argv[1]))
