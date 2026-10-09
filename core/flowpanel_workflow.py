"""File operations for isolated FLOWPanel cases (no GUI or CAD imports)."""
import json
import math
import shutil
import tomllib
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def validate_weber_document(document):
    objects = document.get('documento', {}).get('objetos', [])
    if len(objects) != 1 or objects[0].get('clave') != 'wing':
        raise ValueError('The Weber adapter requires exactly one wing.')
    wing = objects[0]
    p = wing.get('parametros', {})
    if p.get('perfil_raiz') != 'RAE101' or p.get('perfil_punta') != 'RAE101':
        raise ValueError('The isolated-wing adapter currently supports the Weber RAE101 example only.')
    expected = dict(cuerda_raiz_mm=497.84, cuerda_punta_mm=497.84,
                    semi_span_mm=1244.6, flecha_grados=45., diedro_grados=0., torsion_punta_grados=0.)
    for key, value in expected.items():
        if not isinstance(p.get(key), (int, float)) or not math.isclose(p[key], value, rel_tol=1e-10, abs_tol=1e-9):
            raise ValueError(f'The Weber adapter requires {key} = {value}. Other wing geometries are not yet supported.')
    if wing.get('modo_superficie') != 'simetrica' or any(v != 0 for v in wing.get('placement', {}).values()):
        raise ValueError('The Weber wing must be symmetric and have zero translation and rotation.')


def is_weber_case(data):
    return (data.get('adapter') == 'weber_ordered' or
            (data.get('connected_root') is True and data.get('triangulation') == 'mirrored_shortest'))


def mesh_files(data):
    return ('nodes_C.csv', 'cells_C.csv') if is_weber_case(data) else ('surface.msh', 'te_left.msh', 'te_right.msh')


def solver_script(data):
    return ROOT / ('analysis/flowpanel/sweptwing/solve_ordered.jl' if is_weber_case(data)
                   else 'analysis/flowpanel/solve.jl')


def read_case(folder):
    folder = Path(folder)
    data = tomllib.loads((folder / "case.toml").read_text(encoding="utf-8"))
    if is_weber_case(data):
        # Historical Weber cases predate explicit adapter/units metadata.
        data.setdefault('units', 'm')
        data.setdefault('adapter', 'weber_ordered')
    if data.get("units") != "m" or data.get("panels", 0) <= 0:
        raise ValueError("Invalid case units or panel count.")
    for name in mesh_files(data):
        if not (folder / name).is_file():
            raise ValueError(f"Missing mesh: {name}")
    return data


def configure_run(folder, speed, alpha, density):
    """Never modify a mesh case or overwrite previous simulation results."""
    data = read_case(folder)
    if not all(math.isfinite(v) for v in (speed, alpha, density)) or speed <= 0 or density <= 0:
        raise ValueError("Use finite conditions with positive speed and density.")
    limit = 31104 if is_weber_case(data) else 8000
    if data["panels"] > limit:
        raise ValueError(f"This mesh exceeds the {limit:,}-panel limit for this adapter.")
    data.update(speed_mps=speed, aoa_deg=alpha, density_kg_m3=density)
    run = Path(folder) / "runs" / uuid4().hex
    run.mkdir(parents=True)
    for name in mesh_files(data):
        shutil.copyfile(Path(folder) / name, run / name)
    (run / "case.toml").write_text(
        "".join(f"{k} = {json.dumps(v)}\n" for k, v in data.items()), encoding="utf-8")
    return run
