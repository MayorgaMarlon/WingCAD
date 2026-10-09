# Directional mesh study and independent wake-force check

This follow-up tests the apparent stability reported in CONVERGENCE.md with
fixed refinement ratios and separate chord/span changes. It does not reuse the
FLOWPanel tutorial nodes, alter the RAE101 CAD, or fit coefficients to reference
values. All aerodynamic cases keep 30 m/s, 4.2 degrees and 1.225 kg/m3.

## What was changed

The previous continuous structured grid had symmetric nodes but no mirrored
triangle counterparts: all 26,400 triangles in its finest case failed the
reflection check. `mirrored_shortest` triangulates each left-side quadrilateral
using its shortest diagonal and reflects the connectivity onto the right side,
with outward normals and a shared root. Corresponding Cp now agrees to roundoff.

The original cosine distribution creates progressively more unequal intervals.
The optional `bounded` map is t - 0.9 sin(2 pi t)/(2 pi). Its derivative stays
between 0.1 and 1.9 independently of resolution. It limits the parametric size
ratio; it does **not** guarantee well-shaped physical triangles on a curved CAD
surface. Actual area, longest-edge/altitude aspect ratio and triangle quality are
audited separately at the leading edge, trailing edge and tip.

Two nine-case matrices use chord counts 24, 36, 54 per surface and semispan counts
16, 24, 36. Each matrix includes chord-only, span-only and simultaneous changes.
The simultaneous sequence increases both counts by exactly 1.5 at each step.

## Wake diagnostic

`wake_forces.py` extracts circulation from the actual paired trailing-edge
triangles and verifies a continuous spanwise chain. It projects the prescribed
rigid wake onto a plane normal to freestream, then computes unscaled lift and
induced drag using midpoint Trefftz quadrature. There is no empirical loading
shape, clipping, wake relaxation or scaling to match pressure-integrated lift.

The impulse/energy formulation follows the
[MIT TASOPT theory documentation](https://mit-lae.github.io/TASOPT.jl/dev/aero/drag/).
Manufactured checks verify elliptical loading, translation invariance and linear
lift/quadratic drag scaling with circulation. These are independent diagnostic
coefficients; they do not replace the pressure forces in the WingCAD solver.

## Findings from the 18 open-tip cases

With the chord count fixed, increasing span resolution causes large changes in
pressure drag and stronger tip suction. This isolates an anisotropic resolution
and pressure-reconstruction sensitivity; symmetry alone is insufficient.

For the 3072 → 6912 → 15552 panel diagonal sequence:

| Distribution | Last CL change | Last pressure CD change | Last Cp RMS | Last wake CD change |
|---|---:|---:|---:|---:|
| Cosine | 1.474% | 8.753% | 0.02011 | 1.532% |
| Bounded | 1.263% | 3.813% | 0.02059 | 1.557% |

Neither sequence passes all the previous pressure criteria. Wake forces are
less sensitive, but that does not establish surface-pressure convergence.

## Separate closed-tip diagnostic

`--closed-tips` adds the existing CAD planar tip faces to the aerodynamic mesh,
without changing the CAD. This changes the fluid boundary compared with the
open-tip tutorial, so it is a separate diagnostic, not the reference comparison.
Its solver is FLOWPanel's closed-surface least-squares formulation with a
prescribed strength gauge. Normal-velocity maximum and RMS residuals are saved;
they must not be confused with the direct open-surface solve's roundoff residuals.

The rejected direct closed-surface trial failed the no-penetration assertion and
produced no result files. It was replaced with the appropriate least-squares
formulation; the failed trial log remains for traceability.

The three closed runs produced the following diagnostics:

| Panels | CL pressure | CD pressure | CD wake | Raw minimum Cp | Minimum Cp excluding caps | Normal residual RMS, m/s |
|---:|---:|---:|---:|---:|---:|---:|
| 3164 | 0.253889 | 0.00488810 | 0.00452413 | -14.44 | -0.757 | 0.01715 |
| 7052 | 0.257107 | 0.00523866 | 0.00461989 | -29.18 | -0.748 | 0.00592 |
| 15764 | 0.260622 | 0.00596192 | 0.00469021 | -57.35 | -0.954 | 0.00120 |

Closing the tips removes the extreme upper/lower-surface spikes in these runs,
but the extrema move to the sharp tip-cap edges and pressure drag still changes
substantially. Closing the tips is therefore not presented as a convergence fix.

## Reproduction

For either open-tip matrix, select `cosine` or `bounded` and a new output folder:

```powershell
python analysis/flowpanel/sweptwing/prepare_ordered.py --connected --triangulation mirrored_shortest --spacing bounded --output exports/flowpanel/weber/new_directional --resolutions c24_s16:24:16 c36_s16:36:16 c54_s16:54:16 c24_s24:24:24 c36_s24:36:24 c54_s24:54:24 c24_s36:24:36 c36_s36:36:36 c54_s36:54:36
```

Pass the generated case folders to `solve_ordered.jl` as positional arguments.
Then `compare_directional.py --cosine COSINE_STUDY --bounded BOUNDED_STUDY`
produces the comparative HTML, CSV, JSON audit and unsmoothed plots. It deliberately
requires all nine completed cases from both matrices.

The additional chord-resolved sequence uses `coarse:48:16 medium:72:24 fine:108:36`,
bounded spacing and the same mirrored triangulation, retaining the 1.5 refinement
ratio. No acceptance thresholds are relaxed.

Its final values are CL=0.26547637 and CD=0.00503876 on 31,104 panels. The last
changes are CL 1.0061%, CD 5.6125%, Cp RMS 0.01764. The previous pair has Cp RMS
0.02040. Both pairs fail at least one unchanged criterion; more panels alone did
not establish convergence.

`--contour-metric arc` samples the actual OpenCascade section by curve length,
using `GCPnts_AbscissaPoint` rather than x/c station inversion. A separate
3072 → 6912 → 15552 panel bounded-spacing sequence ends at CL=0.26160160,
CD=0.00445405; its last changes are 1.3327% and 1.8284%, with Cp RMS 0.02068.
It also fails the complete acceptance check.

## Pressure-order diagnostic, rejected for the wing

`reconstruct_pressure.py --order 2 --rings 3` fits a quadratic tangent polynomial
to the existing solved strengths. It reproduces a manufactured quadratic field,
but on the chord-resolved wing it gives Cp minima down to -112.64 and strong drag
sensitivity. Some scaled local design matrices have condition numbers above
200,000. These outputs are retained separately under `chord_resolved_quadratic`.

The optional `--adaptive-quadratic` selects support using geometry alone: expand
from three to at most six edge rings until the condition is at most 1000, then
fall back to the original two-ring linear gradient if necessary. It records
expanded and fallback cells. That trial also retains large pressure peaks and
fails convergence (`chord_resolved_adaptive`). Neither quadratic variant is
enabled in the simulator or recommended for this wing. They are retained as
reproducible negative results, not as a correction validated by polynomial tests.

## Complete pressure-chain validation

`validate_sphere.jl` checks the closed-surface solve, induced velocity, gradient
and Bernoulli pressure against the analytic potential-flow sphere solution:
Cp = 1 - 2.25 sin(theta)^2. The source is the
[University of Texas fluid-mechanics notes](https://farside.ph.utexas.edu/teaching/336L/Fluidhtml/node102.html).
RMS errors for 80, 320, 1280 and 5120 panels are 0.13214, 0.08940, 0.05273 and
0.03073. The original 1280-panel check failed the predeclared 0.05 RMS limit;
the 5120-panel extension passes without changing that limit. Both records remain
in the report. Smooth-surface validation does not establish sharp-edge accuracy.

## Final report

[Open the complete investigation](results/directional/report.html).
It contains 28 wing solves, six additional pressure reconstructions, the sphere
validation and the original failed checks. `package_study.py` reproduces the
portable bundle from the completed output directories. The result is **no
demonstrated wing pressure convergence**, not a validated replacement solver.

```powershell
python -m unittest analysis.flowpanel.sweptwing.test_pressure analysis.flowpanel.sweptwing.test_mesh_wake
```

All commands are headless. New outputs live under `exports/flowpanel/weber/`;
previous cases and reports remain preserved.
