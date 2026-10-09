"""Independent rigid-wake Trefftz diagnostic; never rescales pressure forces.

Midpoint point-vortex quadrature in a plane normal to freestream, using the
solved TE circulation. See https://mit-lae.github.io/TASOPT.jl/dev/aero/drag/
for the impulse/energy integrals. No empirical loading or CL rescaling is used.
This is a low-order diagnostic of the prescribed rigid wake, not a relaxed wake.
"""
import numpy as np


def trefftz(trace, circulation, speed, area):
    """trace[:,0:2] = ascending span and freestream-normal height, in metres."""
    assert trace.shape == (len(circulation)+1,2)
    assert np.all(np.diff(trace[:,0])>0) and speed>0 and area>0
    midpoint=(trace[:-1]+trace[1:])/2
    displacement=midpoint[:,None,:]-trace[None,:,:]
    r2=np.sum(displacement**2,axis=2)
    assert np.all(r2>0)
    strength=-np.diff(np.r_[0.,circulation,0.])
    vy=np.sum(-strength*displacement[:,:,1]/(2*np.pi*r2),axis=1)
    vz=np.sum(strength*displacement[:,:,0]/(2*np.pi*r2),axis=1)
    delta=np.diff(trace,axis=0)
    cl=2*np.sum(circulation*delta[:,0])/(speed*area)
    cd=np.sum(circulation*(vy*delta[:,1]-vz*delta[:,0]))/(speed**2*area)
    return float(cl),float(cd)


def from_solution(nodes,cells,fields,config):
    edges={}
    for i,tri in enumerate(cells):
        for a,b in zip(tri,np.roll(tri,-1)):
            if np.max(abs(nodes[[a,b],0]-abs(nodes[[a,b],1])-.49784))<1e-9:
                edges.setdefault(tuple(sorted((a,b))),[]).append(i)
    strips=[]
    for (a,b),pair in edges.items():
        assert len(pair)==2
        upper,lower=sorted(pair,key=lambda i:-nodes[cells[i],2].mean())
        a,b=sorted((a,b),key=lambda n:nodes[n,1])
        # Reverse-boundary upper wake orientation is decreasing y on this mesh;
        # express bound circulation consistently in increasing-span direction.
        circulation=fields['Gamma'][lower]-fields['Gamma'][upper]
        strips.append((nodes[a,1],a,b,circulation))
    strips.sort()
    assert len(strips)==config['wake_segments']
    assert all(a[2]==b[1] for a,b in zip(strips,strips[1:]))
    boundary=nodes[[strips[0][1]]+[s[2] for s in strips]]
    assert np.isclose(boundary[-1,1]-boundary[0,1],config['bref_m'])
    alpha=np.deg2rad(config['aoa_deg'])
    trace=np.column_stack((boundary[:,1],-np.sin(alpha)*boundary[:,0]+np.cos(alpha)*boundary[:,2]))
    circulation=np.array([s[3] for s in strips])
    cl,cd=trefftz(trace,circulation,config['speed_mps'],config['sref_m2'])
    return dict(CL_wake=cl,CD_trefftz=cd,wake_segments=len(strips),
                outer_strip_circulation=float(max(abs(circulation[[0,-1]]))),
                wake_length_m=float(np.linalg.norm(np.diff(boundary,axis=0),axis=1).sum()))
