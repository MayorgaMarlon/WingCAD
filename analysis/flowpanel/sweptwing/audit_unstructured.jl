using TOML, LinearAlgebra
import FLOWPanel as pnl
import GeoIO

folder = abspath(ARGS[1])
grid = pnl.gt.GridTriangleSurface(GeoIO.load(joinpath(folder,"surface.msh")).geometry)
shedding = unique(hcat([pnl.calc_shedding(grid,
    sortslices(pnl.gt.vertices2nodes(GeoIO.load(joinpath(folder,f)).geometry.vertices);dims=2,by=x->x[2]);
    tolerance=.0001*2.4892) for f in ("te_left.msh","te_right.msh")]...);dims=2)
wrong, tested = 0, 0
lengths = Float64[]
for (pi,ia,ib,pj,ja,jb) in eachcol(shedding)
    a,b = pnl.gt.get_cell(grid,pi),pnl.gt.get_cell(grid,pj)
    @assert a[ia] == b[jb] && a[ib] == b[ja]
    push!(lengths,norm(grid._nodes[:,a[ia]]-grid._nodes[:,a[ib]]))
    for ci in (pi+1,pj-1)
        global tested += 1
        if !(1 <= ci <= grid.ncells) || isempty(intersect(pnl.gt.get_cell(grid,ci),[a[ia],a[ib]]))
            global wrong += 1
        end
    end
end
result = Dict("wake_segments"=>size(shedding,2),"wake_edge_length_m"=>sum(lengths),
    "expected_TE_length_m"=>2.4892*sqrt(2),"tested_index_neighbours"=>tested,
    "index_neighbours_not_touching_TE_segment"=>wrong,
    "note"=>"FLOWPanel 2.0.0 force_cellTE uses pi+1/pj-1; these are not topological neighbours on arbitrary triangles")
open(joinpath(folder,"topology_audit.toml"),"w") do io; TOML.print(io,result); end
println(result)
