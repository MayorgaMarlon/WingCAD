# Pressure correction verification

Four candidate reconstructions were evaluated on the same saved circulation
solutions at 6144, 13824 and 31104 panels. No solver calibration, pressure
clipping, reference-node matching, or replacement of pressure forces by wake
forces was used. These are postprocessing experiments, not new flow solves.

- Free affine intercept: rejected; Cp spikes and drag sensitivity increase.
- Recovered nodal potential: rejected; drag refinement fails.
- Parent quadrilateral differentiation: rejected; drag refinement fails.
- Unfolded neighbour triangles: fixes projection error for an intrinsically
  affine potential on a developable curved surface. This is a partial geometric
  consistency correction, not a verified cure for tip pressure.

The unfolded method reduces the last simultaneous CD change from 5.6125% to
4.3433%, but CL changes 1.0260%, exceeding the unchanged 1% criterion. The
first pair also fails Cp RMS (0.020405 versus 0.02). Five additional saved
cross-refinement solutions were reprocessed with unfolding, including the
held-out span extension c72_s36 -> c72_s54. Tip Cp minima remain about -3.83
and -7.53. No candidate was enabled in Julia or the GUI.

Nine manufactured/invariance tests pass. The existing default Python gradient
continues to match the native Julia baseline: maximum component difference
1.8e-11 on the 6144-panel mesh. The curved-surface test demonstrates why
unfolding is mathematically preferable to planar projection there; it does not
validate singular sharp-edge flow. A diverging pointwise edge peak alone does
not establish numerical failure or its cause. Full forces and interior Cp
stability remain the acceptance checks.

Commands (headless):

```powershell
python -m unittest analysis.flowpanel.sweptwing.test_pressure
python analysis/flowpanel/sweptwing/reconstruct_pressure.py exports/flowpanel/weber/chord_resolved exports/flowpanel/weber/unfolded_gradient --unfold
python analysis/flowpanel/sweptwing/reconstruct_pressure.py exports/flowpanel/weber/stability_cross exports/flowpanel/weber/unfolded_cross --unfold
python analysis/flowpanel/sweptwing/assess_pressure_corrections.py
```

All output directories for reconstruction must be fresh. Use --free-intercept,
--recovered, or --quad separately in place of --unfold for the other experiments,
and their matching output paths listed in assess_pressure_corrections.py.
No combinations are allowed. The report generator expects all completed cases.

[Report, original values and failed checks](results/pressure_corrections/report.html).
The correction requested for the wing is **not complete**. A validated solver
change cannot be inferred from these results.
