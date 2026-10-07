"""File operations for isolated FLOWPanel cases (no GUI or CAD imports)."""
import json
import math
import shutil
import tomllib
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def read_case(folder):
    folder = Path(folder)
    data = tomllib.loads((folder / "case.toml").read_text(encoding="utf-8"))
    if data.get("units") != "m" or data.get("panels", 0) <= 0:
        raise ValueError("Invalid case units or panel count.")
    for name in ("surface.msh", "te_left.msh", "te_right.msh"):
        if not (folder / name).is_file():
            raise ValueError(f"Missing mesh: {name}")
    return data


def configure_run(folder, speed, alpha, density):
    """Never modify a mesh case or overwrite previous simulation results."""
    data = read_case(folder)
    if not all(math.isfinite(v) for v in (speed, alpha, density)) or speed <= 0 or density <= 0:
        raise ValueError("Use finite conditions with positive speed and density.")
    if data["panels"] > 8000:
        raise ValueError("This mesh exceeds the 8,000-panel limit. Choose coarse or medium.")
    data.update(speed_mps=speed, aoa_deg=alpha, density_kg_m3=density)
    run = Path(folder) / "runs" / uuid4().hex
    run.mkdir(parents=True)
    for name in ("surface.msh", "te_left.msh", "te_right.msh"):
        shutil.copyfile(Path(folder) / name, run / name)
    (run / "case.toml").write_text(
        "".join(f"{k} = {json.dumps(v)}\n" for k, v in data.items()), encoding="utf-8")
    return run
