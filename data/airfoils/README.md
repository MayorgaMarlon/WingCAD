# RAE 101 section

`rae101.csv` is an unchanged copy of `examples/data/airfoil-rae101.csv`
distributed with FLOWPanel 2.0.0 (BYU FLOW Lab). Columns are x/c and z/c.
The nominal thickness is 12%, with zero camber and a closed trailing edge.

Source: https://github.com/byuflowlab/FLOWPanel.jl/blob/v2.0.0/examples/data/airfoil-rae101.csv
License: [FLOWPanel-LICENSE.txt](FLOWPanel-LICENSE.txt).

WingCAD interpolates each side in cosine angle using a cubic spline, with
zero angle derivative at the trailing edge, then builds its usual OpenCascade
B-spline sections and loft. FLOWPanel uses its own section rediscretization.
Equal coordinate inputs do not imply identical spline surfaces or meshes.
