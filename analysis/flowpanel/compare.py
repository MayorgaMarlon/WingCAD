"""Report mesh sensitivity without treating convergence as physical validation."""

import argparse
from pathlib import Path
import tomllib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Case parent containing coarse/medium/fine")
    parser.add_argument("--levels", nargs="+", choices=("coarse", "medium", "fine"),
                        default=["coarse", "medium", "fine"])
    args = parser.parse_args()
    if len(args.levels) < 2 or len(set(args.levels)) != len(args.levels):
        parser.error("Choose at least two distinct levels in increasing resolution order.")
    cases = []
    for level in args.levels:
        with (args.directory / level / "results" / "coefficients.toml").open("rb") as f:
            cases.append(tomllib.load(f))
    for field in ("source_sha256", "speed_mps", "density_kg_m3", "aoa_deg",
                  "moment_reference_m", "sref_m2", "cref_m", "bref_m", "units", "flowpanel_version"):
        if any(c[field] != cases[0][field] for c in cases[1:]):
            raise ValueError(f"Cannot compare cases with different {field}.")
    if any(a["panels"] >= b["panels"] for a, b in zip(cases, cases[1:])):
        raise ValueError("Panel counts must increase from coarse to fine.")
    print("level       panels          CL      CD_inviscid          Cm")
    for c in cases:
        print(f"{c['level']:8} {c['panels']:9} {c['CL']:12.6g} {c['CD_inviscid']:16.6g} {c['Cm']:12.6g}")
    for a, b in zip(cases, cases[1:]):
        print(f"\nChanges ({a['level']} -> {b['level']}):")
        for field in ("CL", "CD_inviscid", "Cm"):
            change = abs(b[field] - a[field])
            relative = f"{100*change/abs(a[field]):.2f}%" if a[field] else "undefined (zero baseline)"
            print(f"{field}: absolute {change:.6g}, relative {relative}")
    if len(cases) == 2:
        print("Only two levels: a convergence trend cannot yet be established.")
    print("Check that changes decrease. Mesh convergence does not validate the geometry or inviscid model.")


if __name__ == "__main__":
    main()
