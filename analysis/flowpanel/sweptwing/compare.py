"""Reproducible pressure cuts and conservative span loads; no VTK runtime."""
from pathlib import Path
import csv
import json
import tomllib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

ROOT = Path(__file__).resolve().parents[3]
DATA = Path(__file__).parent
OUT = ROOT / "exports/flowpanel/weber"
B = 2.4892
C = B / 5
Q = .5*1.225*30**2
D = np.array([np.cos(np.deg2rad(4.2)),0,np.sin(np.deg2rad(4.2))])
L = np.cross(D,[0,1,0])


def read_vtk(path):
    lines = path.read_text().splitlines()
    def locate(prefix):
        i = next(i for i,s in enumerate(lines) if s.startswith(prefix))
        return i, lines[i].split()
    i,h = locate("POINTS ")
    xyz = np.loadtxt(lines[i+1:i+1+int(h[1])])
    i,h = locate("CELLS ")
    cells = np.loadtxt(lines[i+1:i+1+int(h[1])],dtype=int)
    assert np.all(cells[:,0] == 3)
    triangles = xyz[cells[:,1:]]
    n = len(triangles)
    fields = {}
    for i,s in enumerate(lines):
        if s.startswith("SCALARS "):
            fields[s.split()[1]] = np.loadtxt(lines[i+2:i+2+n])
        elif s.startswith("VECTORS "):
            fields[s.split()[1]] = np.loadtxt(lines[i+1:i+1+n])
    assert all(np.isfinite(v).all() and len(v)==n for v in fields.values())
    return triangles, fields["Cp"], fields["F"]


def section(triangles, cp, eta):
    # Exact plane/triangle intersections; plotted Cp is constant on each panel.
    y = max(eta*B/2, 1e-8)
    records = [[],[]]
    for tri, value in zip(triangles,cp):
        if not tri[:,1].min() <= y <= tri[:,1].max():
            continue
        pts = []
        for a,b in zip(tri,np.roll(tri,-1,axis=0)):
            if (a[1]-y)*(b[1]-y) <= 0 and abs(b[1]-a[1]) > 1e-12:
                pts.append(a+(b-a)*(y-a[1])/(b[1]-a[1]))
        if len(pts) < 2 or np.linalg.norm(pts[0]-pts[1]) < 1e-10:
            continue
        point = np.mean(pts,axis=0)
        side = 0 if point[2]>=0 else 1
        records[side].append(((point[0]-abs(y))/C, value))
    return [np.array(sorted(r)) for r in records]


def area(poly):
    if len(poly)<3:
        return 0.
    return .5*np.linalg.norm(sum((np.cross(poly[i]-poly[0],poly[i+1]-poly[0])
                                 for i in range(1,len(poly)-1)), start=np.zeros(3)))


def clip(poly, y, sign):
    result = []
    for a,b in zip(poly,poly[1:]+poly[:1]):
        ina, inb = sign*(a[1]-y)>=0, sign*(b[1]-y)>=0
        if ina:
            result.append(a)
        if ina != inb:
            result.append(a+(b-a)*(y-a[1])/(b[1]-a[1]))
    return result


def loading(triangles, forces, edges, *, lift=L, drag=D, dynamic_pressure=Q, chord=C):
    result = np.zeros((len(edges)-1,3))
    for tri,force in zip(triangles,forces):
        a = area(tri)
        for i,(lo,hi) in enumerate(zip(edges,edges[1:])):
            if tri[:,1].max() < lo or tri[:,1].min() > hi:
                continue
            poly = clip(clip(list(tri),lo,1),hi,-1)
            result[i] += force * area(poly)/a
    assert np.allclose(result.sum(axis=0),forces.sum(axis=0),rtol=1e-6,atol=1e-6)
    return np.column_stack((result@lift,result@drag))/(np.diff(edges)[:,None]*dynamic_pressure*chord)


def main():
    plots = OUT / "comparison"
    plots.mkdir(exist_ok=True)
    reference_parts = [read_vtk(OUT / f"reference/reference_{side}.vtk") for side in ("L","R")]
    reference = tuple(np.concatenate([p[i] for p in reference_parts]) for i in range(3))
    wingcad = read_vtk(OUT / "wingcad/results/manta.vtk")
    datasets = {"FLOWPanel reference":reference,
                "WingCAD open tips":read_vtk(OUT / "wingcad_open_tips/results/manta.vtk"),
                "WingCAD closed solid":wingcad}
    exp = json.loads((DATA/"experimental.json").read_text())
    colors = {"FLOWPanel reference":"#1976d2","WingCAD open tips":"#e65100",
              "WingCAD closed solid":"#6a1b9a"}
    case_paths = {"FLOWPanel reference":"reference/coefficients.toml",
                  "WingCAD open tips":"wingcad_open_tips/results/coefficients.toml",
                  "WingCAD closed solid":"wingcad/results/coefficients.toml"}
    configs = {name:tomllib.loads((OUT/path).read_text()) for name,path in case_paths.items()}
    for config in configs.values():
        for key,value in dict(speed_mps=30.,aoa_deg=4.2,density_kg_m3=1.225,bref_m=B,sref_m2=B*C).items():
            assert np.isclose(config[key],value), f"Different benchmark condition: {key}"
        assert config['flowpanel_version']==configs['FLOWPanel reference']['flowpanel_version']
    assert configs['WingCAD open tips']['source_sha256']==configs['WingCAD closed solid']['source_sha256']
    cuts = []
    fig,axs = plt.subplots(2,2,figsize=(11,8),sharex=True,sharey=True)
    for ax,eta in zip(axs.flat,(.041,.163,.245,.510)):
        for name,(tri,cp,_) in datasets.items():
            for side,points in enumerate(section(tri,cp,eta)):
                ax.plot(points[:,0],points[:,1],color=colors[name],lw=1.2,
                        label=name if side==0 else None)
                cuts.extend((name,eta,side,float(x),float(v)) for x,v in points)
        key = min(exp['Cp'],key=lambda k:abs(float(k)-eta))
        for side,xkey in enumerate(("weber_xoc_up","weber_xoc_lo")):
            ax.scatter(exp[xkey], [np.nan if x is None else x for x in exp['Cp'][key][side]],
                       s=18,c='black',label='Experimental' if side==0 else None,zorder=5)
        ax.set(title=f"2y/b = {eta}",xlim=(-.02,1.02),ylim=(1,-.9),xlabel="x/c",ylabel="Cp")
        ax.grid(alpha=.2)
    axs[0,0].legend(fontsize=8)
    axs[0,0].set_ylim(max(1,max(r[4] for r in cuts)+.05),min(-.9,min(r[4] for r in cuts)-.05))
    fig.suptitle("Weber swept wing — chordwise pressure, AoA 4.2°")
    fig.tight_layout(); fig.savefig(plots/"chordwise_cp.png",dpi=180); plt.close(fig)
    with (plots/"pressure_sections.csv").open('w',newline='') as stream:
        writer=csv.writer(stream); writer.writerow(('case','2y/b','side_0_upper','x/c','Cp')); writer.writerows(cuts)

    fig,axs = plt.subplots(5,2,figsize=(11,16),sharex=True,sharey=True)
    delta_values = []
    for ax,eta in zip(axs.flat,(0,.04,.08,.16,.24,.51,.65,.9,.95)):
        for name,(tri,cp,_) in datasets.items():
            up,down=section(tri,cp,eta)
            x=np.linspace(max(up[0,0],down[0,0]),min(up[-1,0],down[-1,0]),180)
            delta=np.interp(x,up[:,0],up[:,1])-np.interp(x,down[:,0],down[:,1])
            delta_values.extend(delta)
            ax.plot(x,delta,color=colors[name],label=name)
        raw=np.loadtxt(DATA/f"weber1958-fig2-y2b-{round(eta*100):03}.csv",delimiter=',')
        ax.scatter(raw[:,0],raw[:,1],c='black',s=18,label='Experimental (reference data)')
        ax.set(title=f"2y/b = {eta}",xlim=(-.02,1.02),ylim=(.15,-1.2),xlabel="x/c",ylabel="Cp upper − Cp lower")
        ax.grid(alpha=.2)
    axs[0,0].set_ylim(max(.15,max(delta_values)+.05),min(-1.2,min(delta_values)-.05))
    axs[0,0].legend(fontsize=8); axs[-1,-1].axis('off')
    fig.tight_layout(); fig.savefig(plots/"delta_cp.png",dpi=150); plt.close(fig)

    edges=np.linspace(-B/2,B/2,31)
    # Include CAD/VTK roundoff at the tip planes, including the closed-case caps.
    edges[0] -= 1e-9
    edges[-1] += 1e-9
    eta=(edges[:-1]+edges[1:])/B
    fig,axs=plt.subplots(1,2,figsize=(12,4))
    loads=[]
    coefficients={}
    for name,(tri,cp,forces) in datasets.items():
        load=loading(tri,forces,edges)
        for j,ax in enumerate(axs):
            ax.plot(eta,load[:,j],'.-',color=colors[name],label=name)
        loads.extend((name,float(e),float(a),float(b)) for e,(a,b) in zip(eta,load))
        coefficients[name]=dict(CL=float(forces.sum(axis=0)@L/(Q*B*C)),
            CD_inviscid=float(forces.sum(axis=0)@D/(Q*B*C)),panels=len(tri),Cp_min=float(cp.min()),Cp_max=float(cp.max()))
        saved=configs[name]
        for key in ('CL','CD_inviscid'):
            assert np.isclose(coefficients[name][key],saved[key],rtol=1e-7)
    for ax,key,title in zip(axs,('cls_web','cds_web'),('Sectional lift cl','Sectional drag cd')):
        ys=np.array(exp['y2b_web']); values=np.array(exp[key])
        ax.scatter(np.r_[-ys[::-1],ys],np.r_[values[::-1],values],s=20,c='black',label='Experimental')
        ax.set(xlabel='2y/b',ylabel=title); ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(plots/'spanwise_loading.png',dpi=180); plt.close(fig)
    with (plots/'spanwise_loading.csv').open('w',newline='') as stream:
        writer=csv.writer(stream); writer.writerow(('case','2y/b','cl','cd')); writer.writerows(loads)
    coefficients['experimental']={'CL':exp['CL'],'CD':exp['CD']}
    comparison = {}
    for name in ('WingCAD open tips','WingCAD closed solid'):
        comparison[name] = {key:100*(coefficients[name][key]/coefficients['FLOWPanel reference'][key]-1)
                            for key in ('CL','CD_inviscid')}
    (plots/'coefficients.json').write_text(json.dumps(coefficients,indent=2))
    (plots/'relative_changes_percent.json').write_text(json.dumps(comparison,indent=2))

    fig,axs=plt.subplots(len(datasets),2,figsize=(12,4*len(datasets)))
    for row,(name,(tri,cp,_)) in enumerate(datasets.items()):
        for col,upper in enumerate((True,False)):
            mask=(tri[:,:,2].mean(axis=1)>0)==upper
            # Exclude tip caps from plan-view pressure maps.
            mask &= np.ptp(tri[:,:,1],axis=1)>1e-9
            vertices=tri[mask][:,:,[1,0]].copy(); vertices[:,:,1]*=-1
            pc=PolyCollection(vertices,array=cp[mask],cmap='coolwarm',clim=(-.5,.5),edgecolors='none')
            ax=axs[row,col]; ax.add_collection(pc); ax.autoscale_view(); ax.set_aspect('equal')
            ax.set(title=name+(' — upper' if upper else ' — lower'),xlabel='y (m)',ylabel='−x (m)')
            fig.colorbar(pc,ax=ax,label='Cp (colors clipped to ±0.5)',shrink=.65)
    fig.tight_layout(); fig.savefig(plots/'pressure_top_bottom.png',dpi=180); plt.close(fig)
    rows=''.join(f"<tr><td>{name}</td><td>{v['panels']}</td><td>{v['CL']:.6f}</td><td>{v['CD_inviscid']:.6f}</td></tr>"
                 for name,v in coefficients.items() if name!='experimental')
    figures=''.join(f'<h2>{title}</h2><a href="{file}"><img src="{file}" alt="{title}"></a>'
                    for file,title in (("pressure_top_bottom.png","Presión superior e inferior"),
                     ("chordwise_cp.png","Cp a lo largo de la cuerda"),
                     ("delta_cp.png","Diferencia de presión: superior menos inferior"),
                     ("spanwise_loading.png","Distribución de cargas")))
    changes=comparison['WingCAD open tips']
    html=f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>WingCAD / FLOWPanel — Weber</title>
<style>body{{font:17px system-ui;max-width:1200px;margin:35px auto;padding:0 20px;color:#172b40}}img{{width:100%}}td,th{{padding:12px;border-bottom:1px solid #ccc;text-align:left}}table{{border-collapse:collapse;width:100%}}.note{{background:#fff1d8;padding:20px}}</style>
<h1>Ala Weber: comparación WingCAD / FLOWPanel</h1>
<p>RAE101 · envergadura 2,4892 m · cuerda 0,49784 m · flecha 45° · 30 m/s · 4,2° · 1,225 kg/m³.</p>
<table><tr><th>Caso</th><th>Paneles</th><th>CL</th><th>CD inviscido</th></tr>{rows}
<tr><td>Experimental (datos del ejemplo)</td><td>—</td><td>0.238</td><td>0.005</td></tr></table>
<p class="note">WingCAD con puntas abiertas frente a la referencia: CL {changes['CL']:+.2f} %;
CD inviscido {changes['CD_inviscid']:+.2f} %. No hay convergencia demostrada ni coincidencia validada.
Las oscilaciones locales de presión permanecen visibles; no se han suavizado para aparentar acuerdo.</p>
<p>Los tres casos usan FLOWPanel 2.0.0. La referencia tiene malla estructurada y puntas abiertas.
WingCAD construye un sólido OpenCascade y usa Gmsh. El caso naranja retira las tapas para igualar
el tratamiento de las puntas y usa el mismo sistema directo; el morado conserva el sólido cerrado
y usa mínimos cuadrados. Persisten diferencias de interpolación, triangulación y distribución de paneles.</p>
<p>Los cortes intersectan exactamente el plano y de cada estación; el tutorial usa columnas próximas.
Las cargas usan 30 franjas iguales con reparto de fuerzas por área y conservación verificada.
Todos los campos son finitos y las fuerzas integradas reproducen los coeficientes originales.
Los colores se limitan a ±0,5; los datos CSV conservan los valores completos.</p>
<p><a href="https://flow.byu.edu/FLOWPanel.jl/stable/examples/sweptwing-4p2aoa/">Tutorial de referencia</a> ·
<a href="coefficients.json">Coeficientes JSON</a> · <a href="pressure_sections.csv">Cortes CSV</a> ·
<a href="spanwise_loading.csv">Cargas CSV</a></p>{figures}</html>'''
    (plots/'report.html').write_text(html,encoding='utf-8')
    print(json.dumps(coefficients,indent=2))


if __name__ == '__main__':
    main()
