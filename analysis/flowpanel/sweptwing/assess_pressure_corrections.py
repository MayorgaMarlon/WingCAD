"""Package the pressure-correction experiments without promoting failed methods."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from analysis.flowpanel.sweptwing.reconstruct_pressure import load_fields
from analysis.flowpanel.sweptwing.compare_ordered import sample_panels


def main():
    base=ROOT/'exports/flowpanel/weber'
    output=Path(__file__).parent/'results/pressure_corrections'
    output.mkdir(parents=True,exist_ok=True)
    studies={'Original':'chord_resolved','Free affine intercept':'affine_intercept',
             'Nodal recovery':'recovered_potential','Quad differentiation':'quad_potential',
             'Unfolded triangles':'unfolded_gradient'}
    rows=[];assessments={}
    for name,folder in studies.items():
        study=base/folder
        subprocess.run([sys.executable,str(Path(__file__).with_name('compare_ordered.py')),
                        '--study',str(study)],check=True,stdout=subprocess.DEVNULL)
        summary=json.loads((study/'comparison/convergence.json').read_text())
        assessments[name]=summary
        shutil.copytree(study/'comparison',output/folder,dirs_exist_ok=True)
        for level in ('coarse','medium','fine'):
            cfg=summary['cases'][level]
            rows.append([name,level,cfg['panels'],cfg['CL'],cfg['CD_inviscid'],cfg['Cp_min']])
    with (output/'coefficients.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['method','level','panels','CL','CD_inviscid','Cp_min']);w.writerows(rows)
    # Additional held-out span refinement, unchanged solved circulation.
    data=[];configs=[]
    x,e=np.meshgrid(np.linspace(.01,.99,121),np.linspace(.05,.95,25))
    for key in ('c72_s36','c72_s54'):
        folder=base/'unfolded_cross'/key/'results'
        configs.append(tomllib.loads((folder/'coefficients.toml').read_text()))
        nodes,cells,fields=load_fields(folder/'wing_C.vtk')
        tri=nodes[cells];centers=tri.mean(axis=1);values=[]
        for sign in (1,-1):
            mask=(centers[:,1]>0)&(centers[:,2]*sign>0)
            values.append(sample_panels(tri[mask],fields['Cp'][mask],x,e))
        data.append(np.array(values));assert np.isfinite(data[-1]).all()
    delta=data[1]-data[0]
    span=dict(CL_relative_percent=100*abs(configs[1]['CL']/configs[0]['CL']-1),
              CD_relative_percent=100*abs(configs[1]['CD_inviscid']/configs[0]['CD_inviscid']-1),
              Cp_rms=float(np.sqrt(np.mean(delta**2))),Cp_p95=float(np.quantile(abs(delta),.95)))
    criteria=assessments['Original']['criteria']
    span['passed']=all(v<=criteria[k] for k,v in span.items())
    (output/'audit.json').write_text(json.dumps(dict(studies=assessments,unfolded_span=span,span_cases=configs),indent=2))
    comparison=''
    for name,folder in studies.items():
        s=assessments[name];m=s['pairs'][-1]['metrics'];cfg=s['cases']['fine']
        comparison+=f'<tr><td><a href="{folder}/report.html">{name}</a></td><td>{cfg["CL"]:.7f}</td><td>{cfg["CD_inviscid"]:.7f}</td><td>{cfg["Cp_min"]:.3f}</td><td>{m["CL_relative_percent"]:.3f}</td><td>{m["CD_relative_percent"]:.3f}</td><td>{s["engineering_convergence_passed"]}</td></tr>'
    report=f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>Verificación de correcciones de presión</title>
<style>body{{font:17px system-ui;max-width:1200px;margin:35px auto;padding:15px;color:#183047}}td,th{{padding:12px;border-bottom:1px solid #ccc}}table{{border-collapse:collapse}}.note{{padding:18px;background:#fff0ce}}</style>
<h1>Corrección de presión: resultados de la verificación</h1>
<p class="note"><strong>No hay corrección de las puntas validada todavía.</strong> Se ensayaron cuatro reconstrucciones sobre las mismas soluciones de circulación. Ninguna cumple todos los criterios. No se activaron en el simulador ni se alteraron los resultados originales.</p>
<p>La proyección plana de los vecinos tiene un error geométrico en superficies curvas. Desplegar los triángulos corrige ese error en una prueba de superficie desarrollable con gradiente conocido, pero no elimina la sensibilidad de presión en las puntas del ala. Esta mejora parcial no se presenta como convergencia.</p>
<table><tr><th>Método</th><th>CL fino</th><th>CD fino</th><th>Cp mínimo</th><th>Último cambio CL %</th><th>Último cambio CD %</th><th>Convergencia</th></tr>{comparison}</table>
<h2>Verificación adicional en envergadura</h2><p>Triángulos desplegados, cuerda fija en 72 divisiones y envergadura de 36 a 54: CL cambia {span['CL_relative_percent']:.3f}%, CD {span['CD_relative_percent']:.3f}%; Cp RMS={span['Cp_rms']:.6f}, p95={span['Cp_p95']:.6f}. Cumple todos los criterios de esta pareja: {span['passed']}.</p>
<p>El valor mínimo de Cp sigue pasando de {configs[0]['Cp_min']:.3f} a {configs[1]['Cp_min']:.3f}. Un pico por sí solo no distingue una singularidad de borde de un error numérico; los criterios de fuerza total y presión interior también deben cumplirse.</p>
<h2>Qué se verificó</h2><p>Campos afines, invariancia al potencial constante, permutación, rotación, separación del salto de estela y superficie curva desarrollable. Se conservan la circulación resuelta, la velocidad principal, la malla y las condiciones; sólo cambia la reconstrucción del gradiente y se recalculan velocidad, Cp y fuerzas. Esto no implica nuevas soluciones de circulación. No se suavizó ni recortó Cp para conseguir acuerdo.</p>
<p><a href="coefficients.csv">Coeficientes de todas las pruebas</a> · <a href="audit.json">Auditoría completa</a></p></html>'''
    (output/'report.html').write_text(report,encoding='utf-8')
    print(json.dumps(span,indent=2))


if __name__=='__main__':main()
