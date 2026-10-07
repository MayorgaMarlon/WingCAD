"""Prepare Manta surface meshes without Qt, VTK or a graphical Gmsh session.

Run with WingCAD's Python. Only this analysis path fuses the aircraft bodies.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
LEVELS = {"coarse": (0.24, 0.06), "medium": (0.16, 0.04), "fine": (0.10, 0.025)}


def trailing_points(wing, side, leading=False):
    """Nominal Manta LE/TE in meters, including its tip twist and placement."""
    p = wing["parametros"]
    place = wing["placement"]
    # Deliberately restricted to the shipped Manta layout, not arbitrary aircraft.
    if any(abs(place[k]) > 1e-10 for k in ("roll_deg", "pitch_deg", "yaw_deg", "y_mm")):
        raise ValueError("This Manta adapter requires an unrotated wing on y=0.")
    if wing.get("modo_superficie") != "simetrica":
        raise ValueError("This adapter requires a symmetric wing.")
    f = np.linspace(0, 1, 3001)
    y = f * p["semi_span_mm"]
    chord = p["cuerda_raiz_mm"] * (1-f) + p["cuerda_punta_mm"] * f
    twist = np.radians(f * p["torsion_punta_grados"])
    local_x = (-0.25 if leading else 0.75) * chord
    x = 0.25 * chord + local_x * np.cos(twist) + y * np.tan(np.radians(p["flecha_grados"]))
    z = -local_x * np.sin(twist) + y * np.tan(np.radians(p["diedro_grados"]))
    return np.column_stack((x + place["x_mm"], side*y, z + place["z_mm"])) * 0.001


def surface_step(project, mode, output):
    from app.application import AeroApplication
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    from core.exporter import exportar_step

    app = AeroApplication()
    app.abrir_proyecto(project)
    objects = app.documento.objetos
    wings = [o for o in objects if o.tipo == "Ala"]
    if sorted(o.tipo for o in objects) != ["Ala", "Fuselaje"]:
        raise ValueError("Expected the Manta project: one wing and one center body.")
    chosen = wings if mode == "wing" else list(objects)
    shapes = [BRepBuilderAPI_Copy(o.shape, True, False).Shape() for o in chosen]
    shape = shapes[0]
    for other in shapes[1:]:
        operation = BRepAlgoAPI_Fuse(shape, other)
        operation.Build()
        if not operation.IsDone():
            raise RuntimeError("Analysis-only union failed; no mesh was generated.")
        shape = operation.Shape()
    if shape.IsNull() or not BRepCheck_Analyzer(shape).IsValid():
        raise RuntimeError("The analysis shape is invalid.")
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    count = 0
    while explorer.More():
        count += 1
        explorer.Next()
    if count != 1:
        raise RuntimeError(f"Expected one connected solid, found {count}.")
    exportar_step(shape, output)


def curve_points(gmsh, tag):
    lower, upper = gmsh.model.getParametrizationBounds(1, tag)
    parameters = np.linspace(float(lower[0]), float(upper[0]), 15)
    return np.asarray(gmsh.model.getValue(1, tag, parameters)).reshape(-1, 3)


def identify_edges(gmsh, wing):
    from scipy.spatial import cKDTree
    trees = {(side, leading): cKDTree(trailing_points(wing, side, leading))
             for side in (-1, 1) for leading in (False, True)}
    trailing = {-1: [], 1: []}
    leading = []
    for _, tag in gmsh.model.getEntities(1):
        points = curve_points(gmsh, tag)
        # A tip-closing edge or a tiny residual edge is not a shedding line.
        if np.ptp(points[:, 1]) < 0.002:
            continue
        for (side, is_le), tree in trees.items():
            # 2 mm includes sample spacing and CAD interpolation tolerances.
            if np.max(tree.query(points)[0]) < 0.002:
                (leading if is_le else trailing[side]).append(tag)
    if not all(trailing.values()) or not leading:
        raise RuntimeError("Could not identify both trailing edges and leading edges. Inspect the STEP manually.")
    for tags in trailing.values():
        # Require a connected, unbranched chain; reject ambiguous identification.
        ends = Counter()
        for tag in tags:
            for dim, vertex in gmsh.model.getBoundary([(1, tag)], oriented=False):
                if dim == 0:
                    ends[vertex] += 1
        if sum(v == 1 for v in ends.values()) != 2 or any(v > 2 for v in ends.values()):
            raise RuntimeError("Trailing-edge curves do not form a single open chain.")
    return trailing, leading


def check_mesh(gmsh, trailing):
    node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
    points = dict(zip(map(int, node_tags), np.asarray(coordinates).reshape(-1, 3)))
    kinds, element_tags, node_lists = gmsh.model.mesh.getElements(2)
    if list(kinds) != [2]:
        raise RuntimeError("Expected only linear surface triangles.")
    triangles = np.asarray(node_lists[0], dtype=np.int64).reshape(-1, 3)
    incidence = Counter()
    orientation = Counter()
    volume = 0.0
    seen = set()
    for triangle in triangles:
        key = tuple(sorted(map(int, triangle)))
        if key in seen:
            raise RuntimeError("Duplicate surface triangle.")
        seen.add(key)
        a, b, c = [points[int(i)] for i in triangle]
        if np.linalg.norm(np.cross(b-a, c-a)) < 1e-14:
            raise RuntimeError("Degenerate surface triangle.")
        volume += float(np.dot(a, np.cross(b, c))) / 6
        for u, v in zip(triangle, np.roll(triangle, -1)):
            edge = tuple(sorted((int(u), int(v))))
            incidence[edge] += 1
            orientation[edge] += 1 if u < v else -1
    if any(v != 2 for v in incidence.values()):
        raise RuntimeError("Surface is not watertight/manifold: an edge has other than two adjacent panels.")
    if any(orientation.values()) or abs(volume) < 1e-10:
        raise RuntimeError("Surface orientation is inconsistent or volume is zero.")
    for tags in trailing.values():
        for tag in tags:
            types, _, lines = gmsh.model.mesh.getElements(1, tag)
            if list(types) != [1]:
                raise RuntimeError("Expected linear trailing-edge elements.")
            for a, b in np.asarray(lines[0]).reshape(-1, 2):
                if tuple(sorted((int(a), int(b)))) not in incidence:
                    raise RuntimeError("A trailing-edge segment is not shared by surface panels.")
    quality = gmsh.model.mesh.getElementQualities(element_tags[0], "minSICN")
    return len(triangles), volume, float(min(quality))


def mesh_level(gmsh, step, wing, level, output, source_hash):
    gmsh.clear()
    gmsh.model.add("manta")
    volumes = gmsh.model.occ.importShapes(str(step))
    volumes = [(dim, tag) for dim, tag in volumes if dim == 3]
    if len(volumes) != 1:
        raise RuntimeError("STEP import must produce exactly one volume.")
    gmsh.model.occ.dilate(volumes, 0, 0, 0, 0.001, 0.001, 0.001)
    gmsh.model.occ.synchronize()
    trailing, leading = identify_edges(gmsh, wing)
    maximum, minimum = LEVELS[level]
    gmsh.option.setNumber("Mesh.Algorithm", 6)
    gmsh.option.setNumber("Mesh.ElementOrder", 1)
    gmsh.option.setNumber("Mesh.RecombineAll", 0)
    gmsh.option.setNumber("Mesh.MeshSizeMin", minimum)
    gmsh.option.setNumber("Mesh.MeshSizeMax", maximum)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    distance = gmsh.model.mesh.field.add("Distance")
    gmsh.model.mesh.field.setNumbers(distance, "CurvesList", leading + trailing[-1] + trailing[1])
    gmsh.model.mesh.field.setNumber(distance, "Sampling", 300)
    threshold = gmsh.model.mesh.field.add("Threshold")
    for name, value in {"InField": distance, "SizeMin": minimum, "SizeMax": maximum,
                        "DistMin": 0.04, "DistMax": 0.6}.items():
        gmsh.model.mesh.field.setNumber(threshold, name, value)
    gmsh.model.mesh.field.setAsBackgroundMesh(threshold)
    gmsh.model.mesh.generate(2)
    panels, volume, quality = check_mesh(gmsh, trailing)
    if quality <= 0:
        raise RuntimeError("Invalid triangle quality.")
    gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)
    gmsh.option.setNumber("Mesh.Binary", 0)
    gmsh.option.setNumber("Mesh.SaveAll", 0)
    surfaces = [tag for dim, tag in gmsh.model.getBoundary(volumes, oriented=False) if dim == 2]
    group = gmsh.model.addPhysicalGroup(2, surfaces)
    gmsh.model.setPhysicalName(2, group, "Airframe")
    gmsh.write(str(output / "surface.msh"))
    gmsh.model.removePhysicalGroups()
    for side, filename in ((-1, "te_left.msh"), (1, "te_right.msh")):
        group = gmsh.model.addPhysicalGroup(1, trailing[side])
        gmsh.model.setPhysicalName(1, group, "TrailingEdge")
        gmsh.write(str(output / filename))
        gmsh.model.removePhysicalGroups()
    p = wing["parametros"]
    span = p["semi_span_mm"] * 0.002
    area = p["semi_span_mm"] * (p["cuerda_raiz_mm"] + p["cuerda_punta_mm"]) * 1e-6
    taper = p["cuerda_punta_mm"] / p["cuerda_raiz_mm"]
    chord = (2/3) * p["cuerda_raiz_mm"] * (1+taper+taper*taper)/(1+taper) * 0.001
    metadata = dict(level=level, source_sha256=source_hash, panels=panels,
                    signed_volume_m3=volume, minimum_quality=quality,
                    sref_m2=area, bref_m=span, cref_m=chord,
                    speed_mps=20.0, density_kg_m3=1.225, aoa_deg=4.0,
                    moment_reference_m=[0.9, 0.0, 0.0], units="m")
    with (output / "case.toml").open("w", encoding="utf-8") as f:
        for key, value in metadata.items():
            f.write(f"{key} = {json.dumps(value)}\n")
    print(f"{level}: {panels} panels, min quality {quality:.4g}, signed volume {volume:.6g} m3")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("wing", "aircraft"), default="wing")
    parser.add_argument("--level", choices=(*LEVELS, "all"), default="coarse")
    parser.add_argument("--output", type=Path, default=ROOT / "exports" / "flowpanel" / "manta")
    parser.add_argument("--source", type=Path, default=ROOT / "examples" / "02_manta_uav.wingcad")
    args = parser.parse_args()
    try:
        import gmsh
    except ImportError as error:
        raise SystemExit("Install Gmsh first: python -m pip install -r analysis/flowpanel/requirements.txt") from error
    source = args.source.resolve()
    data = json.loads(source.read_text(encoding="utf-8"))
    if sorted(o["clave"] for o in data["documento"]["objetos"]) != ["fuselage", "wing"]:
        raise ValueError("This adapter requires exactly one wing and one fuselage.")
    wings = [o for o in data["documento"]["objetos"] if o["clave"] == "wing"]
    if len(wings) != 1:
        raise ValueError("Expected exactly one Manta wing.")
    wing = wings[0]
    trailing_points(wing, 1)  # Check supported placement before building CAD.
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    levels = list(LEVELS) if args.level == "all" else [args.level]
    parent = args.output.resolve() / args.mode
    parent.mkdir(parents=True, exist_ok=True)
    if any((parent / level).exists() for level in levels):
        raise FileExistsError("A requested case already exists. Choose a new --output folder to preserve previous runs.")
    with TemporaryDirectory(prefix=".prepare-", dir=parent) as temp:
        step = Path(temp) / "analysis.step"
        surface_step(source, args.mode, step)
        gmsh.initialize(["wingcad-flowpanel"], readConfigFiles=False)
        try:
            for level in levels:
                staging = Path(temp) / level
                staging.mkdir()
                mesh_level(gmsh, step, wing, level, staging, source_hash)
                (staging / "analysis.step").write_bytes(step.read_bytes())
            # Publish only after all requested meshes passed the topology checks.
            for level in levels:
                # Copy into a new directory so Windows inherits the destination
                # ACL instead of retaining TemporaryDirectory's private ACL.
                shutil.copytree(Path(temp) / level, parent / level)
        finally:
            gmsh.finalize()


if __name__ == "__main__":
    main()
