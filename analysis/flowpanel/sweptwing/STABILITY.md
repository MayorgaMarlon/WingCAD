# WingCAD-only stability audit

This study deliberately does not use the reference coefficients as targets.
It extends the existing bounded-spacing directional matrix with independent
CAD meshes c72_s16, c108_s16, c108_s24 and c72_s36, followed by c72_s54. The existing c72_s24 and
c108_s36 cases are reused unchanged. Geometry, source hash, conditions, open
tips, connected root, mirrored triangulation and linear two-ring pressure
reconstruction are fixed and checked by assess_stability.py.

The matrix spans chord counts 36, 54, 72, 108 and half-span counts 16, 24, 36.
Chord ratios are not all identical (1.5, 4/3, 1.5); no Richardson order or
continuum error estimate is inferred. All predeclared pressure and coefficient
thresholds are retained. A direction passes only if its last two pairs pass.
Passing a direction does not override a failed simultaneous refinement study.

The report decomposes signed pressure drag into centroid-based inner 95% and
outer 5% span regions. This diagnostic partition does not remove panels from
the total. Wake-derived forces remain an independent diagnostic, never a
replacement for failing pressure coefficients.

Run without QApplication or VTK:

```powershell
python analysis/flowpanel/sweptwing/prepare_ordered.py --connected --triangulation mirrored_shortest --spacing bounded --output exports/flowpanel/weber/stability_cross --resolutions c108_s24:108:24 c72_s36:72:36 c72_s16:72:16 c108_s16:108:16
julia --startup-file=no --project=analysis/flowpanel analysis/flowpanel/sweptwing/solve_ordered.jl exports/flowpanel/weber/stability_cross/c108_s24 exports/flowpanel/weber/stability_cross/c72_s36 exports/flowpanel/weber/stability_cross/c72_s16 exports/flowpanel/weber/stability_cross/c108_s16
python analysis/flowpanel/sweptwing/assess_stability.py
```

Output folders must be new; existing solve results are preserved. The portable
[report](results/stability/report.html) includes CSV and input SHA-256 hashes.

The workstation has approximately 15.7 GiB physical memory; only 7.7 GiB was
available at the start. A dense 69,984-panel influence matrix alone would need
36.5 GiB (8*N*N bytes), before other arrays. It was not launched. The first four new solves use at most 20,736 panels; the subsequent
span-only c72_s54 extension uses 31,104 panels, already demonstrated feasible. A future larger simultaneous refinement requires
a memory-efficient formulation or a machine with sufficient memory.

The c72_s54 extension uses `prepare_ordered.py --append` with the same
settings and `--resolutions c72_s54:72:54`, followed by solve_ordered.jl on
that case. It is included explicitly, regardless of whether it improves or
worsens the last pair. The original simultaneous failure is retained.

## Completed findings

All five new cases completed. The c72_s36 -> c72_s54 extension changes CL by
0.353669% and pressure CD by 1.632716%, but interior Cp RMS=0.020404 fails
the unchanged 0.02 limit. Cp p95=0.042150 passes. Cp minimum worsens from
-3.82856 to -7.53778, at |2y/b| approximately 0.999.

The signed outer-span CD contribution changes from -0.00120281 to -0.00185117,
while the inner contribution rises from 0.00603919 to 0.00660858. Thus the
small net drag change contains cancellation, not uniformly stabilized pressure.
All three chord-direction sequences pass their last two pairs. The extended
c72 span sequence no longer passes its last two pairs; this negative result is
retained rather than ending the series at its earlier apparently stable level.
The next unresolved task is the tip-region pressure discretization and then a
new fixed-method refinement study; no solver change was adopted in this turn.
