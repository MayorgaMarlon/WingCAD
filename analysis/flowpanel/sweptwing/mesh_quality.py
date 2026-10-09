"""Pure NumPy diagnostics and mirrored triangulation for the Weber CAD grid."""
import numpy as np


def stations(count, spacing='cosine'):
    t = np.linspace(0.,1.,count+1)
    if spacing == 'cosine':
        return (1-np.cos(np.pi*t))/2
    if spacing == 'bounded':
        # Fixed map derivative in [0.1, 1.9]: refinement does not increase
        # the largest/smallest parametric interval ratio without bound.
        return t-.9*np.sin(2*np.pi*t)/(2*np.pi)
    raise ValueError(spacing)


def mirrored_cells(nodes, contour_intervals, half_span_intervals):
    """Triangulate left quads on their shortest diagonal and reflect connectivity."""
    nc, ns = contour_intervals, half_span_intervals
    assert nodes.shape == ((2*ns+1)*nc, 3)
    left = []
    for j in range(ns):
        for i in range(nc):
            a, b = j*nc+i, j*nc+(i+1)%nc
            d, c = a+nc, b+nc
            if np.linalg.norm(nodes[a]-nodes[c]) <= np.linalg.norm(nodes[b]-nodes[d]):
                left.extend(((a,b,c),(a,c,d)))
            else:
                left.extend(((a,b,d),(b,c,d)))
    left = np.asarray(left)
    tri = nodes[left]
    inward = np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])[:,2]*tri[:,:,2].mean(axis=1) < 0
    left[inward] = left[inward][:,[0,2,1]]
    right = (2*ns-left//nc)*nc + left%nc
    assert np.max(abs(nodes[right]-nodes[left]*[1,-1,1])) < 1e-10
    return np.vstack((left,right[:,[0,2,1]]))


def reflection_pairs(nodes, cells):
    def key(triangle):
        return tuple(sorted(tuple(v) for v in np.round(triangle,10)))
    lookup = {key(t):i for i,t in enumerate(nodes[cells])}
    return np.array([lookup.get(key(t*[1,-1,1]),-1) for t in nodes[cells]])


def tip_caps(nodes, contour_intervals, half_span_intervals):
    """Close the two planar CAD tip sections, without introducing new nodes."""
    nc,ns=contour_intervals,half_span_intervals
    assert nc%2==0
    caps=[]
    for offset in (0,2*ns*nc):
        # lower and upper traverse the same x stations TE to LE.
        for k in range(nc//2):
            polygon=list(dict.fromkeys([offset+k,offset+k+1,
                                        offset+(nc-k-1)%nc,offset+(nc-k)%nc]))
            assert len(polygon) in (3,4)
            for j in range(1,len(polygon)-1):
                tri=np.array([polygon[0],polygon[j],polygon[j+1]])
                p=nodes[tri];normal=np.cross(p[1]-p[0],p[2]-p[0])
                assert np.linalg.norm(normal)>0
                if normal[1]*p[0,1]<0:tri=tri[[0,2,1]]
                caps.append(tri)
    return np.array(caps)


def quality(nodes, cells):
    triangles = nodes[cells]
    edges = np.linalg.norm(triangles-np.roll(triangles,1,axis=1),axis=2)
    twice_area = np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)
    assert np.all(twice_area > 0)
    aspect = edges.max(axis=1)**2/twice_area
    q = 2*np.sqrt(3)*twice_area/(edges**2).sum(axis=1)
    centers = triangles.mean(axis=1)
    x = (centers[:,0]-abs(centers[:,1]))/.49784
    eta = 2*abs(centers[:,1])/2.4892
    result = {'panels':len(cells),'unmatched_reflected_triangles':int((reflection_pairs(nodes,cells)<0).sum())}
    for name,mask in {'all':np.ones(len(cells),bool),'leading_edge':x<.05,
                      'trailing_edge':x>.95,'tip':eta>.95}.items():
        result[name] = dict(count=int(mask.sum()),aspect_max=float(aspect[mask].max()),
                            aspect_p95=float(np.quantile(aspect[mask],.95)),quality_min=float(q[mask].min()))
    return result
