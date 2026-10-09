"""Manufactured-field checks, independent of aerodynamic benchmark agreement."""
import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from analysis.flowpanel.sweptwing.reconstruct_pressure import gradient
from analysis.flowpanel.sweptwing.recovered_gradient import recovered_gradient
from analysis.flowpanel.sweptwing.quad_gradient import quad_gradient


def plane():
    nodes=np.array([[x,y,0.] for y in range(5) for x in range(5)])
    cells=[]
    for y in range(4):
        for x in range(4):
            a=y*5+x;cells.extend(((a,a+1,a+6),(a,a+6,a+5)))
    return nodes,np.array(cells)


class PressureGradientTests(unittest.TestCase):
    def test_quad_span_gradient_and_gauge(self):
        ring=np.array([[1.,0.],[0.,-1.],[-1.,0.],[0.,1.]])
        nodes=np.array([[x,y,z] for y in (0.,.4,1.,2.,3.) for x,z in ring])
        cells=[]
        for j in range(4):
            for k in range(4):
                a=j*4+k;b=j*4+(k+1)%4;c=b+4;d=a+4
                cells.extend(((a,b,c),(a,c,d)))
        cells=np.array(cells);gamma=2*nodes[cells].mean(axis=1)[:,1]
        expected=np.tile([0.,-1.,0.],(len(cells),1))
        result=quad_gradient(nodes,cells,gamma,set(),contour_intervals=4)[0]
        np.testing.assert_allclose(result,expected,atol=1e-12)
        permutation=np.random.default_rng(7).permutation(len(cells))
        result=quad_gradient(nodes,cells[permutation],gamma[permutation]+1000,set(),contour_intervals=4)[0]
        np.testing.assert_allclose(result,expected,atol=1e-11)

    def test_unfolded_developable_surface(self):
        flat,cells=plane();radius=8.
        angle=flat[:,0]/radius
        nodes=np.column_stack((radius*np.sin(angle),flat[:,1],radius*(1-np.cos(angle))))
        arc_step=2*radius*np.sin(.5/radius)
        gamma=(2*flat[:,0]*arc_step-3*flat[:,1])[cells].mean(axis=1)
        midpoint_angle=(flat[cells][:,:,0].min(axis=1)+flat[cells][:,:,0].max(axis=1))/(2*radius)
        expected=np.column_stack((-np.cos(midpoint_angle),np.full(len(cells),1.5),-np.sin(midpoint_angle)))
        actual=gradient(nodes,cells,gamma,set(),unfold=True)[0]
        np.testing.assert_allclose(actual,expected,atol=1e-11)

    def test_recovered_affine_gauge_rotation_and_permutation(self):
        nodes,cells=plane();centers=nodes[cells].mean(axis=1)
        gamma=2*centers[:,0]-3*centers[:,1]+7
        expected=np.tile([-1.,1.5,0.],(len(cells),1))
        for reconstruct in (recovered_gradient,lambda *a:gradient(*a,free_intercept=True)):
            np.testing.assert_allclose(reconstruct(nodes,cells,gamma,set())[0],expected,atol=1e-12)
        permutation=np.random.default_rng(19).permutation(len(cells))
        angle=.6;rotation=np.array([[1,0,0],[0,np.cos(angle),-np.sin(angle)],[0,np.sin(angle),np.cos(angle)]])
        actual=recovered_gradient(nodes@rotation.T,cells[permutation],gamma[permutation]+1000,set())[0]
        np.testing.assert_allclose(actual,expected[permutation]@rotation.T,atol=1e-10)

    def test_recovered_wake_jump(self):
        nodes,cells=plane();centers=nodes[cells].mean(axis=1)
        gamma=np.where(centers[:,0]<2,0.,1000.)
        te=set(np.flatnonzero(nodes[:,0]==2))
        result=recovered_gradient(nodes,cells,gamma,te)[0]
        np.testing.assert_allclose(result,0,atol=1e-11)

    def test_quadratic_reconstruction(self):
        nodes,cells=plane();centers=nodes[cells].mean(axis=1)
        x,y=centers[:,:2].T
        gamma=2*x-3*y+.7*x*x+.4*x*y-.2*y*y+8
        expected=-.5*np.column_stack((2+1.4*x+.4*y,-3+.4*x-.4*y,np.zeros_like(x)))
        result=gradient(nodes,cells,gamma,set(),order=2,rings=3)[0]
        np.testing.assert_allclose(result,expected,atol=1e-12)
        adaptive=gradient(nodes,cells,gamma,set(),order=2,rings=3,adaptive=True)[0]
        np.testing.assert_allclose(adaptive,expected,atol=1e-12)
        permutation=np.random.default_rng(12).permutation(len(cells))
        actual=gradient(nodes,cells[permutation],gamma[permutation]+1000,set(),order=2,rings=3)[0]
        np.testing.assert_allclose(actual,expected[permutation],atol=1e-11)

    def test_affine_and_gauge(self):
        nodes,cells=plane();centers=nodes[cells].mean(axis=1)
        gamma=2*centers[:,0]-3*centers[:,1]+7
        result=gradient(nodes,cells,gamma,set())[0]
        np.testing.assert_allclose(result,np.tile([-1,1.5,0],(len(cells),1)),atol=1e-12)
        np.testing.assert_allclose(gradient(nodes,cells,gamma+1000,set())[0],result,atol=1e-11)

    def test_cell_permutation(self):
        nodes,cells=plane();centers=nodes[cells].mean(axis=1)
        gamma=centers[:,0]**2+centers[:,1]
        permutation=np.random.default_rng(42).permutation(len(cells))
        expected=gradient(nodes,cells,gamma,set())[0]
        actual=gradient(nodes,cells[permutation],gamma[permutation],set())[0]
        np.testing.assert_allclose(actual,expected[permutation],atol=1e-12)

    def test_wake_jump_does_not_enter_gradient(self):
        nodes,cells=plane();centers=nodes[cells].mean(axis=1)
        gamma=np.where(centers[:,0]<2,0.,1000.)
        te=set(np.flatnonzero(nodes[:,0]==2))
        result,_,_,wake,_=gradient(nodes,cells,gamma,te)
        self.assertEqual(len(wake),4)
        np.testing.assert_allclose(result,0,atol=1e-12)

    def test_rotated_surface(self):
        nodes,cells=plane();centers=nodes[cells].mean(axis=1)
        gamma=2*centers[:,0]-3*centers[:,1]
        a=.6;rotation=np.array([[1,0,0],[0,np.cos(a),-np.sin(a)],[0,np.sin(a),np.cos(a)]])
        result=gradient(nodes@rotation.T,cells,gamma,set())[0]
        np.testing.assert_allclose(result,np.tile(rotation@[-1,1.5,0],(len(cells),1)),atol=1e-12)


if __name__=='__main__':unittest.main()
