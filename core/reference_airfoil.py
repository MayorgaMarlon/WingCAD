"""RAE101 sampling used by the FLOWPanel Weber benchmark (FITPACK, arc length).

Independent Python implementation of the published sampling specification.
Coordinates are read from the original airfoil table, never from solver results.
"""
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.interpolate import UnivariateSpline
from scipy.optimize import brentq


def spacing(length, count, ratio):
    """GeometricTools' expansion uses linearly varying interval lengths."""
    widths = np.linspace(1.0, ratio, count)
    return np.r_[0.0, np.cumsum(widths * length / widths.sum())]


@lru_cache(maxsize=1)
def reference_sections():
    data = np.loadtxt(Path(__file__).resolve().parents[1] /
                      "data/airfoils/rae101.csv", delimiter=",", skiprows=1)
    leading = np.argmin(data[:, 0])
    stations = np.r_[spacing(.25, 8, 10),
                     .25 + spacing(.5, 8, 1)[1:],
                     .75 + spacing(.25, 8, .1)[1:]]
    sides = []
    for side in (data[:leading+1][::-1], data[leading:]):
        spline = UnivariateSpline(side[:, 0], side[:, 1], k=5, s=1e-8)
        derivative = spline.derivative()
        def arc(x):
            return quad(lambda t: np.hypot(1, derivative(t)), 0, x,
                        epsabs=1e-12, epsrel=1e-12, limit=200)[0]
        total = arc(1)
        xs = [0. if t == 0 else 1. if t >= 1 else
              brentq(lambda x: arc(x)/total-t, 0, 1, xtol=1e-14)
              for t in stations]
        sides.append(np.column_stack((xs, spline(xs))))
    # The periodic reference contour retains upper LE and lower TE.
    sides[1][0] = sides[0][0]
    sides[0][-1] = sides[1][-1]
    return tuple(sides)


def reference_contour():
    upper, lower = reference_sections()
    return np.vstack((lower[::-1], upper[1:-1]))
