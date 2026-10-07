# Import and syntax checks only: no meshing, solver, or graphical window.
import FLOWPanel
import Meshes
import GeoIO

function check_syntax(node, filename)
    node isa Expr || return
    node.head in (:error, :incomplete) && error("Invalid Julia syntax in $filename: $node")
    foreach(child -> check_syntax(child, filename), node.args)
end

for filename in ("setup.jl", "solve.jl")
    check_syntax(Meta.parseall(read(joinpath(@__DIR__, filename), String)), filename)
    println("Syntax OK: ", filename)
end

println("Julia: ", VERSION)
for package in (FLOWPanel, Meshes, GeoIO)
    println(nameof(package), ": ", pkgversion(package))
end
println("Import checks passed. No mesh or simulation was run.")
