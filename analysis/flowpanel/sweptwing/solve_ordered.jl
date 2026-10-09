# Independent CAD nodes, periodic structured topology, and audited rigid wake.
using LinearAlgebra, TOML, DelimitedFiles
import FLOWPanel as pnl
import Meshes
include(joinpath(@__DIR__,"..","topology_gradient.jl"))
BLAS.set_num_threads(4)

# This benchmark does not differentiate through the linear solve. Reuse the
# influence matrix for LU instead of retaining a second dense copy for AD.
function solve_memory_bounded!(solution,matrix,rhs)
    indices=unique(round.(Int,range(1,size(matrix,1);length=min(32,size(matrix,1)))))
    checkrows=copy(matrix[indices,:])
    solution .= rhs
    ldiv!(lu!(matrix),solution)
    @assert norm(checkrows*solution-rhs[indices],Inf) <= 1e-8*max(norm(rhs,Inf),1.)
    return solution
end

function run_ordered(folder)
    config = TOML.parsefile(joinpath(folder,"case.toml"))
    output = joinpath(folder,"results")
    ispath(output) && error("Existing results preserved: $output")
    nc, ns = config["contour_intervals"], config["span_intervals"]
    connected = get(config,"connected_root",false)
    closed = get(config,"closed_tips",false)
    ns = connected ? 2*ns : ns
    BodyType = closed ? pnl.RigidWakeBody{pnl.VortexRing,2} : pnl.RigidWakeBody{pnl.VortexRing,1}
    halves = BodyType[]
    sides = connected ? (("C",1e-14),) : (("L",1e-14),("R",-1e-14))
    for (side, offset) in sides
        nodes = permutedims(readdlm(joinpath(folder,"nodes_$(side).csv"), ',', Float64))
        grid = pnl.gt.Grid([0.,0.,0.], [1.,1.,0.], [nc,ns,0], 1)
        @assert size(nodes) == size(grid.nodes)
        grid.nodes .= nodes
        tri = pnl.gt.GridTriangleSurface(grid, 1)
        if isfile(joinpath(folder,"cells_$(side).csv"))
            @assert config["pressure_reconstruction"] == "least_squares"
            cells=readdlm(joinpath(folder,"cells_$(side).csv"),',',Int)
            points=[Meshes.Point(Tuple(p)) for p in eachcol(nodes)]
            connectivity=[Meshes.connect(Tuple(c),Meshes.Triangle) for c in eachrow(cells)]
            tri=pnl.gt.GridTriangleSurface(Meshes.SimpleMesh(points,connectivity))
        end
        # Pair actual shared TE edges with each panel's own edge orientation.
        pairs = Dict{Tuple{Int,Int},Vector{NTuple{3,Int}}}()
        for ci in 1:tri.ncells
            panel = pnl.gt.get_cell(tri,ci)
            for ia in 1:3
                ib = ia%3+1
                a,b = panel[ia],panel[ib]
                if (a-1)%nc == 0 && (b-1)%nc == 0
                    push!(get!(pairs,minmax(a,b),NTuple{3,Int}[]),(ci,ia,ib))
                end
            end
        end
        shedding = zeros(Int,6,ns)
        for j in 1:ns
            pair = pairs[(1+(j-1)*nc,1+j*nc)]
            @assert length(pair) == 2
            # FLOWPanel's wake uses the reverse boundary orientation. Identify
            # upper/lower geometrically rather than by triangle numbering.
            upper,lower = sort(pair;by=p->sum(nodes[3,n] for n in pnl.gt.get_cell(tri,p[1])),rev=true)
            shedding[:,j] .= (upper[1],upper[3],upper[2],lower[1],lower[3],lower[2])
        end
        @assert size(shedding,2) == ns "Missing or duplicate wake segments"
        @assert all(shedding[4,:] .> 0) "Wake must join upper and lower panels"
        for (pi,ia,ib,pj,ja,jb) in eachcol(shedding)
            @assert ia == ib%3+1 && ja == jb%3+1 "Wake must reverse boundary circulation"
            a, b = pnl.gt.get_cell(tri,pi), pnl.gt.get_cell(tri,pj)
            @assert norm(nodes[:,a[ia]]-nodes[:,b[jb]]) < 1e-10
            @assert norm(nodes[:,a[ib]]-nodes[:,b[ja]]) < 1e-10
            @assert abs(nodes[1,a[ia]]-abs(nodes[2,a[ia]])-.49784)<1e-9
        end
        half = BodyType(tri,shedding;CPoffset=offset)
        normals = pnl.calc_normals(half)
        centers = pnl.calc_controlpoints(half,normals)
        @assert all(abs(normals[3,i])<1e-12 ?
                    normals[2,i]*centers[2,i]>0 : offset*normals[3,i]*centers[3,i]>0
                    for i in 1:half.ncells) "Wrong surface normals"
        push!(halves, half)
    end
    body = closed ? only(halves) : pnl.MultiBody(halves,[s[1] for s in sides])
    @assert body.ncells == config["panels"]
    speed, rho = config["speed_mps"], config["density_kg_m3"]
    alpha = deg2rad(config["aoa_deg"])
    direction = [cos(alpha),0.,sin(alpha)]
    wake = repeat(direction,1,body.nsheddings)
    println("Solving ",folder,": ",body.ncells," panels, ",body.nsheddings," audited wake segments"); flush(stdout)
    elapsed = @elapsed pnl.solve(body,repeat(speed*direction,1,body.ncells),wake,wake;solver=solve_memory_bounded!)
    GC.gc()
    principal=pnl.calcfield_U(body,body)
    residuals=vec(sum(principal.*pnl.calc_normals(body);dims=1))
    normal_residual=maximum(abs.(residuals))
    normal_rms=sqrt(sum(abs2,residuals)/length(residuals))
    if !closed
        @assert normal_residual/speed < 1e-8 "No-flow-through boundary condition failed"
    else
        # Closed surfaces use FLOWPanel's overdetermined least-squares solve.
        # Report all residuals: do not relabel this as an exact collocation solve.
        println("Closed least-squares normal residual: max=",normal_residual," rms=",normal_rms," m/s")
    end
    reconstruction=get(config,"pressure_reconstruction","legacy_flowpanel")
    if reconstruction == "least_squares"
        @assert connected "Least-squares ordered adapter currently requires a connected root"
        config["maximum_scaled_gradient_condition"]=least_squares_gradient!(halves[1])
        if !closed; pnl.add_field(body,"Ugradmu","vector",pnl.get_field(halves[1],"Ugradmu")["field_data"],"cell"); end
    elseif reconstruction == "legacy_flowpanel"
        pnl.calcfield_Ugradmu(body)
    else
        error("Unknown reconstruction: $reconstruction")
    end
    pnl.addfields(body,"Ugradmu","U")
    if reconstruction == "least_squares"
        cp=topology_pressure!(halves[1],speed)
        if !closed; pnl.add_field(body,"Cp","scalar",cp,"cell"); end
    else
        cp=pnl.calcfield_Cp(body,speed)
    end
    @assert all(isfinite,cp)
    pnl.calcfield_F(body,speed,rho;correct_kuttacondition=(reconstruction == "legacy_flowpanel"))
    lift = cross(direction,[0.,1.,0.])
    forces = pnl.calcfield_LDS(body,lift,direction)
    qS = .5*rho*speed^2*config["sref_m2"]
    result = merge(config,Dict("CL"=>dot(forces[:,1],lift)/qS,
        "CD_inviscid"=>dot(forces[:,2],direction)/qS,"Cp_min"=>minimum(cp),"Cp_max"=>maximum(cp),
        "wake_segments"=>body.nsheddings,"solve_seconds"=>elapsed,
        "linear_solver"=>"in-place LU, 32 sampled equation residual checks",
        "normal_velocity_residual_mps"=>normal_residual,
        "normal_velocity_rms_mps"=>normal_rms,
        "boundary_solver"=>(closed ? "closed least squares, prescribed constant-strength gauge" : "open direct"),
        "flowpanel_version"=>string(pkgversion(pnl))))
    mkpath(output); pnl.save(body,closed ? "wing_C" : "wing";path=output)
    open(joinpath(output,"coefficients.toml"),"w") do io; TOML.print(io,result); end
    println("CL=",result["CL"]," CD=",result["CD_inviscid"]); flush(stdout)
end

if abspath(PROGRAM_FILE) == @__FILE__
    for folder in ARGS; run_ordered(abspath(folder)); GC.gc(); end
end
