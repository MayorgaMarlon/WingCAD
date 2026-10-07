"""Built-in section coordinates, independent of external profile file paths."""
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline
from OCP.gp import gp_Pnt
from core.naca import puntos_naca4


def airfoil_points(codigo, cuerda, numero_puntos):
    if codigo.upper() == "RAE101F":
        from core.reference_airfoil import reference_sections
        return tuple([gp_Pnt(float(x*cuerda), 0, float(z*cuerda))
                      for x, z in side] for side in reference_sections())
    if codigo.upper() != "RAE101":
        return puntos_naca4(codigo, cuerda, numero_puntos)
    data = np.loadtxt(Path(__file__).resolve().parents[1] / "data/airfoils/rae101.csv",
                      delimiter=",", skiprows=1)
    leading = int(np.argmin(data[:, 0]))
    theta = np.linspace(0, np.pi, numero_puntos)
    x = (1-np.cos(theta))/2
    sections = []
    for side in (data[:leading+1][::-1], data[leading:]):
        # Interpolate in cosine angle to resolve the rounded leading edge.
        # dz/dtheta=0 at the trailing edge gives a finite dz/dx there and
        # prevents a not-a-knot spline from crossing the opposite surface.
        spline = CubicSpline(np.arccos(1-2*side[:, 0]), side[:, 1],
                             bc_type=((2, 0.0), (1, 0.0)))
        z = spline(theta)
        z[0] = z[-1] = 0.0
        sections.append([gp_Pnt(float(a*cuerda), 0, float(b*cuerda)) for a,b in zip(x,z)])
    return tuple(sections)
