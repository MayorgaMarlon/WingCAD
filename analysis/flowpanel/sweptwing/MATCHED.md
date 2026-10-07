# Matched Weber tutorial benchmark

Open `examples/09_weber_matched_reference.wingcad` in WingCAD. This is a wing
with a dedicated `RAE101F` profile (both root and tip, exactly 25 points per side).
The old example 08 and unstructured Gmsh results remain available unchanged.

The original tutorial script is the specification: span 2.4892 m, chord
0.49784 m, leading-edge sweep 45 degrees, taper 1, twist and dihedral zero;
30 m/s, alpha 4.2 degrees, density 1.225 kg/m³. Both cases use FLOWPanel 2.0.0,
2880 triangles, 15 span intervals per half-wing, 48 contour intervals,
open tips, two bodies, the direct vortex-ring system and a rigid wake aligned
with the freestream. CPoffset is +1e-14 left and -1e-14 right.

## Geometry and independence

`core/reference_airfoil.py` independently samples the original RAE101 CSV using
SciPy FITPACK degree 5, smoothing 1e-8, normalized arc length and the published
interval expansion. GeometricTools implements this expansion using linearly
varying widths, not a geometric progression. The periodic contour retains the
upper leading-edge point and lower trailing-edge point, including their tiny
nonzero smoothed ordinates.

WingBuilder builds smooth OpenCascade interpolating section curves through these
stations and lofts the wing. `prepare_matched.py` obtains every mesh coordinate by
projection onto that BRep, checks distance and validity, and exports STEP and CSV.
No reference VTK or pressure result is read to build this geometry.

`reference.jl OUTPUT CAD_NODES_FOLDER` generates the original topology, checks
the independently generated CAD nodes against the reference, substitutes only
coordinates and constructs fresh unsolved bodies. Connectivity, neighbours,
trailing-edge shedding and all solver settings remain those of the tutorial.
It then performs a new solve and postprocessing. Reference forces and Cp are
never solver input. Without the second argument it executes the original case.

This is a reproduction of the **same discretized problem** through WingCAD.
The continuous interpolating CAD curve between mesh nodes is not asserted to be
identical to FITPACK. It does not validate arbitrary Gmsh meshes or establish
physical accuracy or convergence. The remaining discrepancy with experiment is
the tutorial's discrepancy, not eliminated by this match.

## Reproduce (PowerShell, project root)

Use fresh output directories; preparation and solver refuse existing cases.
The installed Python environment and Julia project are required.

```powershell
python analysis/flowpanel/sweptwing/prepare_matched.py
julia --startup-file=no --project=analysis/flowpanel analysis/flowpanel/sweptwing/reference.jl exports/flowpanel/weber/wingcad_matched exports/flowpanel/weber/matched_geometry
python analysis/flowpanel/sweptwing/compare_matched.py
python analysis/flowpanel/sweptwing/test_matched.py
```

Reference results must exist under `exports/flowpanel/weber/reference`; generate
them with `reference.jl exports/flowpanel/weber/reference` (no second argument).
`prepare_matched.py --output PATH` permits another geometry output path; the
comparison script uses the canonical folders above.

The general GUI **Prepare mesh** action still uses the Manta/Gmsh adapter; it is
not the structured Weber benchmark pipeline. Use these commands for this case.
The example itself is editable and viewable in WingCAD's Design tab.

## Results and checks

Report: `exports/flowpanel/weber/matched_comparison/report.html`.

| Case | CL | CD inviscid |
|---|---:|---:|
| Original FLOWPanel script | 0.271560782984 | 0.006597903106 |
| WingCAD BRep + FLOWPanel | 0.271560783010 | 0.006597903113 |
| Experiment | 0.238 | 0.005 |

Maximum node difference: 4.24e-10 m. Maximum per-triangle Cp difference:
6.54e-8. Projection distance on the WingCAD BRep: less than 7.2e-13 mm.
`comparison.json` contains full precision, conditions and input hashes.

Pressure plots follow `slicefield`: nearest span column and average of each
triangle pair, then shift x by its minimum and divide by chord. Actual sampled
span positions appear in the plots/CSV. Delta Cp pairs upper and lower panels.
Sectional loads follow `calcfield_sectionalforce`'s center-spacing convention.
These reductions are the tutorial procedure; there is no extra smoothing.
Raw panel-by-panel agreement and integrated forces are checked separately.

Original tutorial and data attribution: see `FLOWPanel-LICENSE.txt`, the headers
in `reference.jl` and `data/airfoils/README.md`.
