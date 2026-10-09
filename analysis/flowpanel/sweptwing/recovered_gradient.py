"""Experimental continuous-potential recovery; never averages or clips Cp.

Reconstruct nodal potential from affine-exact cell extrapolation, then take the
gradient of the nodal linear triangle. Keep separate nodal sectors at wake cuts.
This is a diagnostic until the complete fixed-method refinement checks pass.
"""
import numpy as np
from analysis.flowpanel.sweptwing.reconstruct_pressure import gradient


def recovered_gradient(nodes, cells, gamma, te_nodes, **kwargs):
    base, normals, areas, wake, condition = gradient(nodes, cells, gamma, te_nodes, **kwargs)
    sign = kwargs.get('normal_sign', 1)
    centers = nodes[cells].mean(axis=1)
    potential_gradient = -2*base/sign
    incident = [[] for _ in nodes]
    for i, tri in enumerate(cells):
        for node in tri:
            incident[node].append(i)
    # A vertex fan is traversed only across non-wake edges. This prevents
    # transfer of the potential jump even when both surfaces share TE nodes.
    edge_cells = {}
    for i, tri in enumerate(cells):
        for a, b in zip(tri, np.roll(tri, -1)):
            edge_cells.setdefault(tuple(sorted((a, b))), []).append(i)
    result = np.zeros_like(base)
    cache = {}
    for i, tri in enumerate(cells):
        values = []
        for node in tri:
            seen = {i}; todo = [i]
            while todo:
                k = todo.pop()
                for other in cells[k]:
                    if other == node or (node in te_nodes and other in te_nodes):
                        continue
                    for j in edge_cells[tuple(sorted((node, other)))]:
                        if j not in seen and normals[j]@normals[i] > .5:
                            seen.add(j); todo.append(j)
            key = (node, tuple(sorted(seen)))
            if key not in cache:
                ids = np.array(key[1])
                offsets = nodes[node]-centers[ids]
                estimates = gamma[ids]+np.sum(potential_gradient[ids]*offsets, axis=1)
                cache[key] = np.average(estimates, weights=areas[ids])
            values.append(cache[key])
        edges = nodes[tri[1:]]-nodes[tri[0]]
        # Minimum-norm solution is tangent to this triangle and exactly
        # reproduces the two nodal potential differences.
        slope = np.linalg.lstsq(edges, np.array(values[1:])-values[0], rcond=1e-12)[0]
        result[i] = -.5*sign*slope
    return result, normals, areas, wake, condition
