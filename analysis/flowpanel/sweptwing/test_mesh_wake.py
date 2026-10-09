"""Numerical checks for mirrored connectivity and independent wake forces."""
import unittest
import numpy as np
from analysis.flowpanel.sweptwing.mesh_quality import mirrored_cells,reflection_pairs,stations,tip_caps
from analysis.flowpanel.sweptwing.wake_forces import trefftz


class MeshWakeTests(unittest.TestCase):
    def test_closed_tip_manifold(self):
        nc,ns=16,4
        angle=np.arange(nc)*2*np.pi/nc
        nodes=np.array([[abs(y)+(1+np.cos(t))/2,y,-.06*np.sin(t)]
                        for y in np.linspace(-1,1,2*ns+1) for t in angle])
        cells=np.vstack((mirrored_cells(nodes,nc,ns),tip_caps(nodes,nc,ns)))
        edges={}
        for tri in cells:
            for a,b in zip(tri,np.roll(tri,-1)):
                edges.setdefault(tuple(sorted((a,b))),[]).append((a,b))
        self.assertTrue(all(len(v)==2 and v[0]==v[1][::-1] for v in edges.values()))
        tri=nodes[cells]
        np.testing.assert_allclose(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]).sum(axis=0),0,atol=1e-12)

    def test_mirror_and_normals(self):
        nc,ns=16,4
        angle=np.arange(nc)*2*np.pi/nc
        nodes=np.array([[abs(y)+(1+np.cos(t))/2,y,-.06*np.sin(t)]
                        for y in np.linspace(-1,1,2*ns+1) for t in angle])
        cells=mirrored_cells(nodes,nc,ns)
        pairs=reflection_pairs(nodes,cells)
        self.assertTrue(np.all(pairs>=0))
        np.testing.assert_array_equal(pairs[pairs],np.arange(len(cells)))
        tri=nodes[cells]
        self.assertTrue(np.all(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])[:,2]*tri[:,:,2].mean(axis=1)>0))

    def test_bounded_spacing(self):
        for n in (16,32,64,128):
            s=stations(n,'bounded');delta=np.diff(s)
            self.assertGreater(delta.min(),0)
            self.assertLessEqual(delta.max()/delta.min(),19.000001)
            np.testing.assert_allclose(s,1-s[::-1],atol=1e-15)

    def test_elliptic_wake(self):
        # b=2, S=1, V=10, Gamma0=1: CL=pi/10, CD=CL^2/(pi*AR).
        errors=[]
        for n in (100,200,400):
            y=np.linspace(-1,1,n+1);mid=(y[:-1]+y[1:])/2
            cl,cd=trefftz(np.column_stack((y,np.zeros_like(y))),np.sqrt(1-mid**2),10,1)
            self.assertLess(abs(cl/(np.pi/10)-1),.002)
            errors.append(abs(cd/(np.pi/400)-1))
        self.assertLess(errors[-1],.01)
        self.assertTrue(all(a>b for a,b in zip(errors,errors[1:])))

    def test_wake_translation_and_strength_scaling(self):
        y=np.linspace(-1,1,101);trace=np.column_stack((y,.05*abs(y)))
        gamma=np.sqrt(1-((y[:-1]+y[1:])/2)**2)
        cl,cd=trefftz(trace,gamma,10,1)
        np.testing.assert_allclose(trefftz(trace+[3,7],2*gamma,10,1),[2*cl,4*cd],rtol=1e-12)


if __name__=='__main__':unittest.main()
