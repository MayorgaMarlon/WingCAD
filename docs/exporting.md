# Exporting from WingCAD

Use **Export selected object...** or **Export project...**. In the save dialog,
choose the format from the file-type list and enter a filename. The selected
format determines the extension; a conflicting extension is replaced. STEP
remains the default. Project export includes all valid components, including
hidden ones, in their current positions and orientations.

| Format | Contents and units |
| --- | --- |
| STEP / STP | Exact CAD geometry. Complete projects use the existing multibody-part exporter with assembly generation disabled temporarily. |
| BREP | Native OpenCascade geometry and topology, in WingCAD millimeters. Projects are compounds of independent shapes. |
| STL | Binary triangle mesh, coordinates in millimeters (STL itself has no unit metadata). |
| GLB | Single binary glTF file with named component nodes. Coordinates are converted from millimeters/Z-up to meters/Y-up. |
| OBJ | Text triangle mesh with a named object per component, coordinates in millimeters and Z-up. No material sidecar is generated. |

GLB uses OpenCascade's native glTF writer. OBJ and GLB do not export the viewer's
selection highlight, CG markers or material appearance. The mesh deflection is
0.5 mm with an angular deflection of 0.2 radians. Export triangulation is computed
on copies, leaving the displayed CAD shapes unchanged. No exporter needs a VTK
renderer or a QApplication.

No Boolean union between project components is performed. In particular, an STL
of overlapping bodies is not automatically a single watertight printable model.
Mesh formats approximate curved surfaces; use STEP or BREP for exact CAD exchange.
Continue saving `.wingcad` projects to preserve editable parameters.

Writers use a temporary destination and replace the final file only after a
successful write. STEP's previous assembly setting is restored even on failure.

Implementation reference for GLB units and axes:
[Khronos glTF specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html).

Verification for this change is limited to Python compilation and imports, per
the requested execution limits. No GUI was launched and exported files have not
yet been checked in external CAD programs or mesh viewers.
