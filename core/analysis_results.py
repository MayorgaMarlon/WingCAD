"""Display rows for saved simulation results; no GUI or VTK dependencies."""
import math


def result_tables(data):
    def rows(specification):
        return [(label, data[key], unit) for key, label, unit in specification if key in data]

    conditions = rows([
        ('speed_mps', 'Speed', 'm/s'), ('aoa_deg', 'Angle of attack', 'deg'),
        ('density_kg_m3', 'Air density', 'kg/m³'), ('sref_m2', 'Reference area', 'm²'),
        ('bref_m', 'Reference span', 'm'), ('panels', 'Surface panels', ''),
        ('level', 'Mesh resolution', ''), ('wake_segments', 'Wake segments', ''),
        ('pressure_reconstruction', 'Pressure method', ''),
    ])
    results = rows([
        ('CL', 'Lift coefficient CL', ''), ('CD_inviscid', 'Inviscid drag coefficient CD', ''),
        ('Cm', 'Moment coefficient Cm', ''), ('Cp_min', 'Minimum Cp', ''),
        ('Cp_max', 'Maximum Cp', ''), ('solve_seconds', 'Linear solve time', 's'),
        ('normal_velocity_residual_mps', 'Maximum normal velocity residual', 'm/s'),
    ])
    if all(k in data for k in ('speed_mps', 'density_kg_m3', 'sref_m2')):
        speed, density, area = (data[k] for k in ('speed_mps', 'density_kg_m3', 'sref_m2'))
        if all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0 for v in (speed, density, area)):
            q = .5*density*speed**2
            results.append(('Dynamic pressure', q, 'Pa'))
            for key, label in [('CL', 'Lift (CL × q × S)'), ('CD_inviscid', 'Inviscid drag (CD × q × S)')]:
                if key in data:
                    results.append((label, data[key]*q*area, 'N'))
    return results, conditions


def display_value(value):
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    if isinstance(value, float):
        return f'{value:.7g}'
    return str(value)
