# Read exported meshes and identify wake edges without solving or opening a GUI.
using TOML
import FLOWPanel as pnl
import GeoIO
import Meshes

for folder in ARGS
    config = TOML.parsefile(joinpath(folder, "case.toml"))
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
    size(shedding, 2) > 0 || error("No shedding panels in $folder")
    if get(config, "solver_formulation", "closed_least_squares") == "direct_open_surface"
        offset = config["normal_sign"] > 0 ? 1e-14 : -1e-14
        body = pnl.RigidWakeBody{pnl.VortexRing, 1}(grid, shedding; CPoffset=offset)
    else
        offset = config["signed_volume_m3"] > 0 ? 1e-14 : -1e-14
        body = pnl.RigidWakeBody{pnl.VortexRing, 2}(grid, shedding; CPoffset=offset)
    end
    body.ncells == config["panels"] || error("Panel count mismatch in $folder")
    println(folder, ": ", body.ncells, " panels, ", body.nsheddings, " shedding edges; OK")
end
