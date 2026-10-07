# Independent WingCAD mesh refinement

This study uses `examples/08_weber_swept_wing.wingcad`, standard RAE101,
160 points per section and 3 CAD loft sections. It does not use RAE101F,
the matched example 09, reference nodes or reference connectivity.

The wing is rebuilt with WingBuilder/OpenCascade, exported once to STEP and
meshed independently by Gmsh at three resolutions. The same STEP hash is
recorded in every case. Span, chord, sweep, taper, twist, dihedral and flow
conditions are the same nominal values as the Weber tutorial: 2.4892 m,
0.49784 m, 45°, 1, 0°, 0°, 30 m/s, alpha 4.2°, density 1.225 kg/m³.

Both sides use the same original RAE101 coordinate table, but the CAD's
interpolation differs from the tutorial's smoothing spline. This is measured
separately, without changing either geometry to improve agreement.

## Refinement protocol

| Level | Maximum size (m) | Minimum size (m) | Open-tip panels |
|---|---:|---:|---:|
| Coarse | 0.18 | 0.0375 | 2806 |
| Medium | 0.12 | 0.025 | 6214 |
| Fine | 0.08 | 0.0166667 | 13734 |

Size limits decrease by 1.5 each step; the edge-distance field and CAD remain
fixed. Gmsh algorithm 6, first-order triangles, one thread. These are independent,
non-nested unstructured meshes. Tip caps are removed at every level to match
the tutorial's open-tip condition. Parent meshes are watertight with positive
volume, nondegenerate triangles and consistent edge orientation; the only
boundary edges after cap removal lie on the tip planes. The exported trailing
edges are those of the actual CAD mesh.

All cases use FLOWPanel's direct vortex-ring formulation, rigid wake aligned
with freestream, default kernel settings, outward control-point offset 1e-14
and identical reference area. The unstructured adapter has one connected body;
the tutorial has two structured half-wing bodies. Gradient reconstruction and
body partition therefore remain methodological differences.

FLOWPanel emits a winding-number warning on the open surface. The logs retain
it. Closed-parent orientation and open-tip topology were checked; this is not
a claim that the winding warning is independently resolved.

## Run (WingCAD Python environment, project root)

```powershell
python analysis/flowpanel/sweptwing/independent_meshes.py
julia --startup-file=no --project=analysis/flowpanel analysis/flowpanel/solve.jl exports/flowpanel/weber/independent/coarse 18000
julia --startup-file=no --project=analysis/flowpanel analysis/flowpanel/solve.jl exports/flowpanel/weber/independent/medium 18000
julia --startup-file=no --project=analysis/flowpanel analysis/flowpanel/solve.jl exports/flowpanel/weber/independent/fine 18000
python analysis/flowpanel/sweptwing/compare_independent.py
```

Julia may be invoked using its installed absolute path if not on PATH.
Preparation and solves refuse to overwrite existing cases. Use `--output PATH`
to prepare another study; the comparison script reads the canonical path above.
The existing original reference must be present in `exports/flowpanel/weber/reference`.
No Qt application or VTK rendering is started by these commands.

## Measured results

| Case | CL | CD inviscid |
|---|---:|---:|
| FLOWPanel tutorial, 2880 panels | 0.271560783 | 0.006597903 |
| WingCAD coarse | 0.233826421 | 0.012776129 |
| WingCAD medium | 0.250461964 | 0.011032696 |
| WingCAD fine | 0.250999152 | 0.009197027 |

Coarse→medium: CL +7.11%, CD −13.65%. Medium→fine: CL +0.214%, CD −16.64%.
Fine versus reference: CL −7.57%, CD +39.39%.

The small final CL change is evidence of reduced sensitivity for this pair of
meshes, not a convergence proof. Drag and local Cp remain mesh-sensitive;
oscillations are retained in the plots. No Richardson extrapolation, GCI or
geometry-only aerodynamic error is asserted without an established asymptotic
regime. The 2880-panel reference itself is not a demonstrated continuum solution.

At y=622.3 mm, 802 dense samples on the continuous reference profile have a
maximum one-way distance to the CAD section of 0.5767 mm, RMS 0.1010 mm. This
sampled sectional metric is not a Hausdorff bound. It quantifies representation
differences but does not tell how much of CL/CD discrepancy they cause.

Thus this study distinguishes **measured geometry differences** from **mesh
sensitivity on fixed geometry**. It does not uniquely apportion the aerodynamic
residual between geometry, mesh, gradient reconstruction and body partition.
Further work should first address mesh quality/distribution and Cp convergence,
then use controlled geometry variants with the same solver/meshing procedure.

## Artifacts and verification

Report: `exports/flowpanel/weber/independent/comparison/report.html`.
The report includes refinement curves, raw Cp cuts, top/bottom pressure,
conservative span loads, sectional geometry distances, CSV and full JSON audit.
All case conditions and hashes are checked before comparison. Integrated panel
forces reproduce the saved coefficients and conservative span bands reproduce
the total force. The raw pressure fields must all be finite.

Pressure extraction is the same plane/triangle intersection for every mesh,
not the tutorial's nearest-column reduction. Lines connect panel samples and
do not smooth them. Span loads use 30 common bands with polygon clipping and
area-weighted force integration. Color maps use ±0.5, without altering raw Cp.

The general GUI Prepare mesh action remains the Manta adapter. Use the commands
above for this dedicated benchmark; example 08 opens normally in the Design tab.
