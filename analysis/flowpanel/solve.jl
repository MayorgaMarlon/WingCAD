# Headless surface-panel case. Never launches ParaView or a GUI.
# API workflow: https://flow.byu.edu/FLOWPanel.jl/stable/examples/blendedwingbody-aero/
using TOML
using LinearAlgebra
import FLOWPanel as pnl
import GeoIO
import Meshes

function run_case(folder, maxpanels)
    config = TOML.parsefile(joinpath(folder, "case.toml"))
    config["units"] == "m" || error("Expected meshes already converted to meters.")
    config["panels"] <= maxpanels || error("Panel limit exceeded; refine the configuration or explicitly increase the limit.")
    output = joinpath(folder, "results")
    ispath(output) && error("Results already exist. Use a new case directory to preserve previous runs.")

    mesh = GeoIO.load(joinpath(folder, "surface.msh")).geometry
    grid = pnl.gt.GridTriangleSurface(mesh)
    edges = map(("te_left.msh", "te_right.msh")) do filename
        line = GeoIO.load(joinpath(folder, filename)).geometry
        points = pnl.gt.vertices2nodes(line.vertices)
        sortslices(points; dims=2, by=x -> x[2])
    end
    shedding = hcat([pnl.calc_shedding(grid, edge; tolerance=0.0001*config["bref_m"])
                     for edge in edges]...)
    shedding = unique(shedding; dims=2)
    size(shedding, 2) > 0 || error("No trailing-edge panels were identified.")
    formulation = get(config, "solver_formulation", "closed_least_squares")
    if formulation == "direct_open_surface"
        offset = config["normal_sign"] > 0 ? 1e-14 : -1e-14
        body = pnl.RigidWakeBody{pnl.VortexRing, 1}(grid, shedding; CPoffset=offset)
    elseif formulation == "closed_least_squares"
        offset = config["signed_volume_m3"] > 0 ? 1e-14 : -1e-14
        body = pnl.RigidWakeBody{pnl.VortexRing, 2}(grid, shedding; CPoffset=offset)
    else
        error("Unknown solver formulation: $formulation")
    end
    body.ncells == config["panels"] || error("Imported panel count differs from the Gmsh audit.")

    alpha = deg2rad(config["aoa_deg"])
    speed = config["speed_mps"]
    rho = config["density_kg_m3"]
    speed > 0 && rho > 0 || error("Speed and density must be positive.")
    direction = [cos(alpha), 0.0, sin(alpha)]
    inflow = repeat(speed * direction, 1, body.ncells)
    wake_a = repeat(direction, 1, body.nsheddings)
    wake_b = copy(wake_a)
    println("Solving $(body.ncells) panels, $(body.nsheddings) shedding panels on CPU.")
    elapsed = @elapsed pnl.solve(body, inflow, wake_a, wake_b)
    pnl.calcfield_U(body, body)
    pnl.calcfield_Ugradmu(body)
    pnl.addfields(body, "Ugradmu", "U")
    cp = pnl.calcfield_Cp(body, speed)
    all(isfinite, cp) || error("Non-finite pressure coefficients; inspect the mesh and wake.")
    pnl.calcfield_F(body, speed, rho)
    span_direction = [0.0, 1.0, 0.0]
    lift_direction = cross(direction, span_direction)
    forces = pnl.calcfield_LDS(body, lift_direction, direction)
    moments = pnl.calcfield_lmn(body, config["moment_reference_m"],
                               direction, span_direction, lift_direction)
    normalization = 0.5 * rho * speed^2 * config["sref_m2"]
    result = copy(config)
    result["CL"] = dot(forces[:, 1], lift_direction) / normalization
    result["CD_inviscid"] = dot(forces[:, 2], direction) / normalization
    result["Cm"] = dot(moments[:, 2], span_direction) / (normalization * config["cref_m"])
    result["Cp_min"] = minimum(cp)
    result["Cp_max"] = maximum(cp)
    result["solve_seconds"] = elapsed
    result["julia_version"] = string(VERSION)
    result["flowpanel_version"] = string(Base.pkgversion(pnl))
    all(isfinite, [result["CL"], result["CD_inviscid"], result["Cm"]]) || error("Invalid integrated coefficients.")
    mkpath(output)
    pnl.save(body, "manta"; path=output)
    open(joinpath(output, "coefficients.toml"), "w") do io
        TOML.print(io, result)
    end
    println("CL=$(result["CL"]), CD_inviscid=$(result["CD_inviscid"]), Cm=$(result["Cm"])")
    println("Saved to $output. Inspect normals/wake and compare all three mesh levels before interpreting results.")
end

if isempty(ARGS)
    error("Usage: julia --project=analysis/flowpanel analysis/flowpanel/solve.jl CASE_DIRECTORY [MAX_PANELS=8000]")
end
run_case(abspath(ARGS[1]), length(ARGS) > 1 ? parse(Int, ARGS[2]) : 8000)
