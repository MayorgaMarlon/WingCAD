# Run with: julia --project=analysis/flowpanel analysis/flowpanel/setup.jl
import Pkg
Pkg.activate(@__DIR__)
Pkg.add([
    Pkg.PackageSpec(name="FLOWPanel"),
    Pkg.PackageSpec(name="Meshes"),
    Pkg.PackageSpec(name="GeoIO"),
])
Pkg.instantiate()
Pkg.precompile()
println("FLOWPanel environment ready. Keep Project.toml and Manifest.toml to reproduce it.")
