# Independent CAD mesh convergence

This study keeps example 08's WingCAD/OpenCascade RAE101 wing: span 2.4892 m,
chord 0.49784 m, sweep 45 degrees, no twist or dihedral. Conditions are 30 m/s,
4.2 degrees and 1.225 kg/m3. It uses neither tutorial nodes nor its profile
interpolant. Sampled nodes are checked against the actual CAD surface.

## Changes

- Independent cosine chord/span spacing; shared root nodes and open aerodynamic
  tips. The CAD solid itself is unchanged.
- Each rigid wake segment uses its actual upper/lower trailing-edge pair, checked
  connectivity and reverse boundary orientation, aligned with the freestream.
- Weighted tangent-plane least-squares gradient over two edge-neighbour rings,
  excluding the wake cut. FLOWPanel's structured pi+1/pj-1 neighbour assumptions
  are inappropriate for arbitrary Gmsh cell numbering.
- Equal pressure only on actual paired trailing-edge triangles. Forces use that
  same Cp without a second index-based correction. Raw extrema are retained.
- In-place dense LU saves memory. Sampled linear-system residuals and full
  no-penetration residuals are checked.

`solve.jl` defaults to `pressure_reconstruction = "least_squares"`. Explicitly
set `pressure_reconstruction = "legacy_flowpanel"` for historical postprocessing.
The potential-flow equations remain unchanged; pressure reconstruction changes.

## Reproduce headlessly

From the repository root, with the WingCAD Python environment and Julia:

```powershell
python analysis/flowpanel/sweptwing/prepare_ordered.py --connected --output exports/flowpanel/weber/new_convergence --levels coarse medium fine ultra extended verification
julia --startup-file=no --project=analysis/flowpanel analysis/flowpanel/sweptwing/solve_ordered.jl exports/flowpanel/weber/new_convergence/coarse exports/flowpanel/weber/new_convergence/medium exports/flowpanel/weber/new_convergence/fine exports/flowpanel/weber/new_convergence/ultra exports/flowpanel/weber/new_convergence/extended exports/flowpanel/weber/new_convergence/verification
python analysis/flowpanel/sweptwing/compare_ordered.py --study exports/flowpanel/weber/new_convergence
python -m unittest analysis.flowpanel.sweptwing.test_pressure
```

The coefficient plot reads the previously generated reference benchmark at
`exports/flowpanel/weber/reference/coefficients.toml`.

Current diagnostics are under `exports/flowpanel/weber/ordered_ls`. They reuse
saved circulation and principal velocity from `ordered_connected`, reconstructing
pressure with `reconstruct_pressure.py`; the parent VTK hash is recorded. This
avoids repeating unchanged potential solves. Native Julia and independent Python
reconstruction agree on the 1536-panel check (maximum Cp difference below 1e-12).

## Acceptance and limitations

Criteria saved before the runs require two successive refinements with CL change
at most 1%, CD change at most 5%, sampled Cp RMS difference at most 0.02 and
95th-percentile difference at most 0.05. Unsmoothened triangle Cp is sampled on
a fixed interior domain: x/c=0.01 to 0.99, |2y/b|=0.05 to 0.95.

These are engineering sensitivity checks, not Richardson extrapolation or a
continuum error bound. Final spacing ratios are smaller than initial ratios:
small adjacent changes alone do not demonstrate asymptotic convergence. Raw
tip-pressure singularities and their drag contributions remain in the report.
Full-surface pointwise convergence is not claimed. Tutorial agreement is not an
acceptance criterion: its finite mesh and profile interpolant differ from the CAD.

Four manufactured Python tests cover affine gradients, constant-strength offset
invariance, cell renumbering, wake jumps and 3D rotation. These checks alone do
not establish aerodynamic accuracy.

## Measured results (2026-10-07)

| Panels | CL | CD inviscid |
|---:|---:|---:|
| 1536 | 0.2537512 | 0.00537069 |
| 3456 | 0.2565713 | 0.00513995 |
| 7776 | 0.2605803 | 0.00512517 |
| 17280 | 0.2650540 | 0.00515033 |
| 21600 | 0.2663464 | 0.00514896 |
| 26400 | 0.2675078 | 0.00513986 |

The last two pairs pass the stated engineering checks. Final changes are
0.4361% in CL, 0.1768% in CD, Cp RMS 0.01617 and Cp p95 0.03590.
However, CL still trends upward and raw tip Cp reaches -23.13. This is limited
mesh sensitivity acceptance, not proof of asymptotic or full-surface convergence.
The tutorial's finite-grid values are CL=0.2715608, CD=0.00659790; disagreement
remains, particularly in drag, and cannot yet be attributed solely to geometry.

Headless integration smoke checks also generated finite results on the original
unstructured Weber mesh (2806 panels, CL 0.24730945, CD 0.01340818) and Manta
aircraft mesh (3410 panels, CL 0.16180619, CD 0.00738091). Those single-level
checks verify solver compatibility only, not convergence of arbitrary Gmsh
meshes. FLOWPanel reports a winding-number warning for the open Weber surface;
open-tip topology is intentional in this benchmark. The old outputs are retained.

The portable report snapshot is [results/convergence/report.html](results/convergence/report.html).
