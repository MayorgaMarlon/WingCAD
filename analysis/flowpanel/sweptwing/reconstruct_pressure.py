"""Topology-aware surface gradient reconstruction on saved FLOWPanel solutions.

Keeps the solved doublet strengths and principal-value induced velocities.
Reconstructs their surface jump with weighted local linear least squares,
blocking cross-wake stencils. No pressure clipping or fitting to reference data.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tomllib
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))


def load_fields(path):
    lines=path.read_text().splitlines()
    i=next(i for i,s in enumerate(lines) if s.startswith('POINTS '))
    nodes=np.loadtxt(lines[i+1:i+1+int(lines[i].split()[1])])
    i=next(i for i,s in enumerate(lines) if s.startswith('CELLS '))
    count=int(lines[i].split()[1]);cells=np.loadtxt(lines[i+1:i+1+count],dtype=int)[:,1:]
    fields={}
    for i,s in enumerate(lines):
        if s.startswith('SCALARS '): fields[s.split()[1]]=np.loadtxt(lines[i+2:i+2+count])
        if s.startswith('VECTORS '): fields[s.split()[1]]=np.loadtxt(lines[i+1:i+1+count])
    return nodes,cells,fields


def gradient(nodes,cells,gamma,te_nodes,normal_sign=1,order=1,rings=2,adaptive=False,diagnostics=None,free_intercept=False,unfold=False):
    assert order in (1,2) and rings>=2
    assert not adaptive or (order==2 and rings<=6)
    stats=diagnostics if diagnostics is not None else {}
    stats.update(expanded_stencil_cells=0,linear_fallback_cells=0,maximum_candidate_condition=0.)
    triangles=nodes[cells];centers=triangles.mean(axis=1)
    vectors=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    areas=np.linalg.norm(vectors,axis=1)/2;normals=vectors/(2*areas[:,None])
    assert np.all(areas>0)
    adjacency=[[] for _ in cells];edges={};wake=[]; shared={}
    for i,tri in enumerate(cells):
        for a,b in zip(tri,np.roll(tri,-1)):
            edges.setdefault(tuple(sorted((a,b))),[]).append(i)
    for (a,b),neighbors in edges.items():
        assert len(neighbors)<=2
        if a in te_nodes and b in te_nodes:
            assert len(neighbors)==2
            wake.append(neighbors)
        elif len(neighbors)==2:
            i,j=neighbors;adjacency[i].append(j);adjacency[j].append(i)
            shared[i,j]=shared[j,i]=(a,b)
    result=np.zeros_like(centers);conditions=[]
    for i in range(len(cells)):
        seen={i};frontier={i}
        transforms={i:(np.eye(3),np.zeros(3))}
        tangent=triangles[i,1]-triangles[i,0];tangent/=np.linalg.norm(tangent)
        bitangent=np.cross(normals[i],tangent)

        def fit(neighbors,degree):
            required=2 if degree==1 else 5
            if free_intercept:
                assert degree==1 and not adaptive
                required+=1
            if len(neighbors)<required:return None,float('inf')
            displacement=centers[neighbors]-centers[i]
            if unfold:
                displacement=np.array([transforms[j][0]@centers[j]+transforms[j][1]-centers[i] for j in neighbors])
            design=np.column_stack((displacement@tangent,displacement@bitangent))
            scale=np.sqrt(np.mean(design**2,axis=0));assert min(scale)>1e-15
            weight=1/np.maximum(np.linalg.norm(displacement,axis=1),1e-15)
            coordinates=design/scale
            basis=coordinates if degree==1 else np.column_stack((coordinates,coordinates[:,0]**2/2,
                                                               coordinates[:,0]*coordinates[:,1],coordinates[:,1]**2/2))
            if free_intercept:
                # Fit a local affine field instead of forcing a noisy panel value
                # to be the exact intercept. Include the center with a finite
                # geometry-derived weight; no flow/reference-dependent tuning.
                basis=np.column_stack((basis,np.ones(len(neighbors))))
                basis=np.vstack((basis,[0.,0.,1.]))
                weight=np.r_[weight,1/np.median(np.linalg.norm(displacement,axis=1))]
                rhs=np.r_[gamma[neighbors]-gamma[i],0.]
            else:
                rhs=gamma[neighbors]-gamma[i]
            matrix=basis*weight[:,None]
            slope,_,rank,singular=np.linalg.lstsq(matrix,rhs*weight,rcond=1e-12)
            condition=float(singular[0]/singular[-1]) if rank==required else float('inf')
            if np.isfinite(condition):stats['maximum_candidate_condition']=max(stats['maximum_candidate_condition'],condition)
            if rank!=required:return None,condition
            slope=slope[:2]/scale
            return -.5*normal_sign*(slope[0]*tangent+slope[1]*bitangent),condition

        used=0
        for ring in range(1,(6 if adaptive else rings)+1):
            following=set()
            for k in sorted(frontier):
                for j in sorted(adjacency[k]):
                    if j in seen or j in following or normals[j]@normals[i]<=.5:continue
                    following.add(j)
                    if unfold:
                        # Unfold the neighbouring triangle around its shared
                        # edge; compose rotations along the BFS surface path.
                        axis=np.cross(normals[j],normals[k]);cosine=normals[j]@normals[k]
                        skew=np.array([[0.,-axis[2],axis[1]],[axis[2],0.,-axis[0]],[-axis[1],axis[0],0.]])
                        rotation=np.eye(3)+skew+skew@skew/(1+cosine)
                        anchor=nodes[shared[k,j][0]]
                        rk,tk=transforms[k]
                        transforms[j]=(rk@rotation,rk@(anchor-rotation@anchor)+tk)
            seen.update(following);frontier=following
            if ring==2:linear_neighbors=sorted(seen-{i})
            if ring<rings:continue
            value,condition=fit(sorted(seen-{i}),order);used=ring
            if not adaptive or (value is not None and condition<=1000):break
        if adaptive and (value is None or condition>1000):
            value,condition=fit(linear_neighbors,1);stats['linear_fallback_cells']+=1
        if used>rings:stats['expanded_stencil_cells']+=1
        assert value is not None, 'Degenerate tangent gradient stencil'
        conditions.append(condition);result[i]=value
    return result,normals*normal_sign,areas,wake,max(conditions)


def save_vtk(path,nodes,cells,fields):
    with path.open('w') as stream:
        stream.write('# vtk DataFile Version 3.0\nWingCAD local gradient reconstruction\nASCII\nDATASET UNSTRUCTURED_GRID\n')
        stream.write(f'POINTS {len(nodes)} double\n');np.savetxt(stream,nodes,fmt='%.17g')
        stream.write(f'CELLS {len(cells)} {len(cells)*4}\n')
        np.savetxt(stream,np.column_stack((np.full(len(cells),3),cells)),fmt='%d')
        stream.write(f'CELL_TYPES {len(cells)}\n');np.savetxt(stream,np.full(len(cells),5),fmt='%d')
        stream.write(f'CELL_DATA {len(cells)}\n')
        for name,values in fields.items():
            if values.ndim==1:stream.write(f'SCALARS {name} double\nLOOKUP_TABLE default\n')
            else:stream.write(f'VECTORS {name} double\n')
            np.savetxt(stream,values,fmt='%.17g')


def process(study,output,append=False,order=1,rings=2,adaptive=False,free_intercept=False,recovered=False,quad=False,unfold=False):
    if sum((free_intercept,recovered,quad,unfold))>1:
        raise ValueError('Test one reconstruction change at a time')
    if any((free_intercept,recovered,quad,unfold)) and (order!=1 or rings!=2 or adaptive):
        raise ValueError('These experiments require fixed linear order and two rings')
    if output.exists() and not append:raise FileExistsError(output)
    if append:
        assert (study/'criteria.json').read_bytes()==(output/'criteria.json').read_bytes()
    else:
        output.mkdir(parents=True)
        shutil.copyfile(study/'criteria.json',output/'criteria.json')
    for folder in sorted(study.iterdir()):
        if not (folder/'results/coefficients.toml').exists():continue
        if append and (output/folder.name).exists():continue
        config=tomllib.loads((folder/'results/coefficients.toml').read_text())
        assert config.get('connected_root'), 'This command expects the connected independent CAD grid'
        source=folder/'results/wing_C.vtk';nodes,cells,fields=load_fields(source)
        te=set(np.flatnonzero(abs(nodes[:,0]-abs(nodes[:,1])-.49784)<1e-9))
        diagnostics={}
        reconstruct=gradient
        if recovered:
            from analysis.flowpanel.sweptwing.recovered_gradient import recovered_gradient
            reconstruct=recovered_gradient
        if quad:
            from analysis.flowpanel.sweptwing.quad_gradient import quad_gradient
            def reconstruct(*a,**kw):
                return quad_gradient(*a,contour_intervals=config['contour_intervals'],**kw)
        grad,normals,areas,wake,condition=reconstruct(nodes,cells,fields['Gamma'],te,order=order,rings=rings,adaptive=adaptive,diagnostics=diagnostics,free_intercept=free_intercept,unfold=unfold)
        assert len(wake)==config['wake_segments']
        principal=fields['U']-fields['Ugradmu']
        velocity=principal+grad
        raw_cp=1-np.sum(velocity**2,axis=1)/config['speed_mps']**2
        cp=raw_cp.copy()
        # Only the actual paired TE panels receive the same Kutta pressure.
        for i,j in wake:cp[i]=cp[j]=(raw_cp[i]+raw_cp[j])/2
        q=.5*config['density_kg_m3']*config['speed_mps']**2
        force=-cp[:,None]*q*areas[:,None]*normals
        direction=np.array([np.cos(np.deg2rad(config['aoa_deg'])),0,np.sin(np.deg2rad(config['aoa_deg']))])
        lift=np.cross(direction,[0,1,0]);total=force.sum(axis=0)/(q*config['sref_m2'])
        method=('unfolded triangles' if unfold else 'quad potential' if quad else
                'recovered nodal potential' if recovered else 'free affine intercept' if free_intercept else 'projected triangles')
        config.update(CL=float(total@lift),CD_inviscid=float(total@direction),Cp_min=float(cp.min()),Cp_max=float(cp.max()),
                      pressure_reconstruction=f'{method}; weighted tangent least squares, order {order}, {rings} edge rings, wake cut',
                      gradient_polynomial_order=order,gradient_rings=rings,
                      adaptive_stencil=adaptive,
                      free_intercept=free_intercept,
                      recovered_nodal_potential=recovered,
                      quad_potential=quad,
                      unfolded_stencil=unfold,
                      experimental_reconstruction=(order==2 or free_intercept or recovered or quad or unfold),
                      parent_solution_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                      maximum_scaled_gradient_condition=condition,
                      normal_velocity_max_mps=float(np.max(abs(np.sum(principal*normals,axis=1)))))
        config.update(diagnostics)
        target=output/folder.name/'results';target.mkdir(parents=True)
        fields.update(U=velocity,Ugradmu=grad,Cp=cp,F=force,Cp_before_Kutta=raw_cp)
        save_vtk(target/'wing_C.vtk',nodes,cells,fields)
        shutil.copyfile(folder/'case.toml',target.parent/'case.toml')
        wake_file=folder/'results/wing_C_wake.vtk'
        if wake_file.exists():shutil.copyfile(wake_file,target/wake_file.name)
        (target/'coefficients.toml').write_text(''.join(f'{k} = {json.dumps(v)}\n' for k,v in config.items()))
        print(folder.name,config['CL'],config['CD_inviscid'],config['Cp_min'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--append',action='store_true')
    parser.add_argument('--order',type=int,choices=(1,2),default=1,help='Order 2 is experimental and has failed the current Weber convergence checks')
    parser.add_argument('--rings',type=int,default=2)
    parser.add_argument('--adaptive-quadratic',action='store_true',help='Geometry-only conditioning check: expand to six rings, then use linear fallback if condition exceeds 1000')
    parser.add_argument('--free-intercept',action='store_true',help='Experimental affine fit with a fitted intercept; not enabled in the simulator')
    parser.add_argument('--recovered',action='store_true',help='Experimental nodal potential recovery; not enabled in the simulator')
    parser.add_argument('--quad',action='store_true',help='Experimental CAD quadrilateral potential differentiation')
    parser.add_argument('--unfold',action='store_true',help='Unfold neighbour triangles into the target tangent plane before fitting')
    args=parser.parse_args();process(args.study.resolve(),args.output.resolve(),args.append,args.order,args.rings,args.adaptive_quadratic,args.free_intercept,args.recovered,args.quad,args.unfold)
