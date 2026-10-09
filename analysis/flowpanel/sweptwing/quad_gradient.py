"""Benchmark-only potential differentiation on independent CAD quadrilaterals.

Triangle strengths are area-integrated to their parent surface quadrilateral;
differentiate potential and geometry with the same nonuniform three-point
operator, then map derivatives to each actual triangle's tangent plane.
No pressure averaging, clipping, reference nodes or prescribed tip circulation.
"""
import numpy as np


def quad_gradient(nodes,cells,gamma,te_nodes,contour_intervals,**kwargs):
    nc=contour_intervals
    assert len(nodes)%nc==0
    ns=len(nodes)//nc-1
    tri=nodes[cells];centers=tri.mean(axis=1)
    cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    areas=np.linalg.norm(cross,axis=1)/2
    normals=cross/(2*areas[:,None])
    rows=np.min(cells//nc,axis=1)
    columns=np.empty(len(cells),dtype=int)
    for i,cell in enumerate(cells):
        indices=set(cell%nc)
        assert len(indices)==2 and len(set(cell//nc))==2
        columns[i]=nc-1 if indices=={0,nc-1} else min(indices)
    group=rows*nc+columns
    counts=np.bincount(group,minlength=ns*nc)
    assert np.all(counts==2), 'Exactly two triangles required per CAD quadrilateral'
    weights=np.bincount(group,weights=areas,minlength=ns*nc)
    potential=(np.bincount(group,weights=areas*gamma,minlength=ns*nc)/weights).reshape(ns,nc)
    position=np.column_stack([np.bincount(group,weights=areas*centers[:,j],minlength=ns*nc)/weights for j in range(3)]).reshape(ns,nc,3)
    ring=nodes[:nc]
    arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(np.vstack((ring,ring[0])),axis=0),axis=1))]
    s=(arc[:-1]+arc[1:])/2
    y=nodes.reshape(ns+1,nc,3)[:,0,1]
    y=(y[:-1]+y[1:])/2
    assert np.all(np.diff(y)>0) and np.all(np.diff(s)>0)
    dg_y,dg_s=np.gradient(potential,y,s,edge_order=2)
    dr_y=np.gradient(position,y,axis=0,edge_order=2)
    dr_s=np.gradient(position,s,axis=1,edge_order=2)
    result=np.zeros_like(centers)
    for i,(r,c) in enumerate(zip(rows,columns)):
        tangent=np.stack((dr_y[r,c],dr_s[r,c]))
        tangent-=np.outer(tangent@normals[i],normals[i])
        result[i]=-.5*np.linalg.lstsq(tangent,[dg_y[r,c],dg_s[r,c]],rcond=1e-12)[0]
    edges={}
    for i,tri in enumerate(cells):
        for a,b in zip(tri,np.roll(tri,-1)):
            if a in te_nodes and b in te_nodes:
                edges.setdefault(tuple(sorted((a,b))),[]).append(i)
    assert all(len(pair)==2 for pair in edges.values())
    return result,normals,areas,list(edges.values()),0.
