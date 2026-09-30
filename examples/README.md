# Complete aircraft examples

Use **Open project** in WingCAD, then **Fit** to frame the aircraft.
These projects contain complete external configurations, not isolated components.

| Project | Configuration |
| --- | --- |
| [01_complete_aircraft.wingcad](01_complete_aircraft.wingcad) | Conventional aircraft with fuselage, main wing and both stabilizers. Based on the existing WingCAD v5 project. |
| [02_manta_uav.wingcad](02_manta_uav.wingcad) | Original tailless UAV concept with a flattened center body and a broad swept wing. Inspired by the general BWB layout in the AeroShape reference, with different dimensions and native WingCAD components. |
| [03_sierra_glider.wingcad](03_sierra_glider.wingcad) | 17 m span glider with a slender fuselage and T-tail. |
| [04_kestrel_twin_boom.wingcad](04_kestrel_twin_boom.wingcad) | 8 m span UAV with a central pod, two tail booms, connecting tailplane and twin fins. |
| [05_orbit_box_wing.wingcad](05_orbit_box_wing.wingcad) | 7 m span box-wing concept with upper/lower wings and vertical tip connectors. |
| [06_atlas_cargo.wingcad](06_atlas_cargo.wingcad) | 18 m long cargo transport with a 20 m span high wing and T-tail. |
| [07_aurora_airliner.wingcad](07_aurora_airliner.wingcad) | 28 m long regional airliner with a 25 m span swept wing, two pylons and hollow nacelles. |

## Reference and implementation

The aircraft example categories in the supplied `AeroShape.zip` guided this
collection. All new dimensions and assemblies were defined for WingCAD's own
project format and native OpenCascade builders. No AeroShape source, dependencies,
FreeCAD integration or visualization patches were copied or added.

These are editable external aircraft concepts, not detailed production models.
WingCAD currently provides straight-axis elliptical fuselages and root-to-tip
tapered wings. The examples do not reproduce guided BWB blends, curved glider
booms, custom cargo cross-sections or smoothly blended winglets. The box-wing
connectors are independent bodies, not filleted joints. Engine interiors,
propellers, landing gear, equipment and flight controls are not represented.

The new examples use illustrative shell mass settings for wings and fuselages.
The airliner nacelles use the actual geometric wall volume. These values are
not aircraft weight estimates or evidence of aerodynamic stability.

## Manta UAV

- Wingspan: 6,000 mm; center-body length: 2,800 mm.
- Center body: 1,100 mm wide and 380 mm high.
- Wing root/tip chords: 2,000 / 400 mm; sweep: 28 degrees.
- Root/tip airfoils: NACA 0018 / 0010.
- Dihedral: 2 degrees; tip twist: -2 degrees.
- Two editable components: `UAV center body` and `UAV swept wing`.
- Illustrative shell mass model: 1.5 mm thickness and 1,600 kg/m3 density.

This is a geometric concept, not an aerodynamically validated aircraft.
Propulsion, control surfaces and internal equipment are not modeled.
The body and wing overlap and remain independent; their intersection is not a
smooth, fused BWB surface. The current WingCAD wing uses one root-to-tip taper,
not the reference's multi-segment wing. No AeroShape dependencies, visualization
patches or custom Boolean fusion code are included.

The shell setting estimates mass; it does not hollow out the exported solids.
Overlapping component contributions are included in the global mass calculation.
The conventional example retains its original solid mass model and density.

## Editing and export

Select components in the document tree to edit their parameters. Save an edited
copy under a new name in `projects` to preserve these examples.

The new examples have custom positions. Avoid **Arrange components**, which uses the
application's conventional-aircraft placement rules; edit **Position and
orientation** directly instead. Reopen the example to restore its layout.

Use **Export project as STEP part** for a multibody STEP. The project exporter
keeps independent bodies in one product without joining the wing and body.

No GUI or VTK session was launched to create these examples. The new aircraft
have not yet been rebuilt or visually inspected in WingCAD. Verification is
limited to source compilation and safe imports, following the requested limits.
