# Analytic smooth-surface check of the complete solve/velocity/pressure chain.
# For a sphere: Cp = 1 - 9/4 sin(theta)^2, theta measured from freestream.
# No Qt, VTK runtime, or graphical viewer is initialized.
include(joinpath(@__DIR__,"solve_ordered.jl"))

function sphere(level)
    t=(1+sqrt(5.))/2
    vertices=[[-1.,t,0.],[1.,t,0.],[-1.,-t,0.],[1.,-t,0.],
              [0.,-1.,t],[0.,1.,t],[0.,-1.,-t],[0.,1.,-t],
              [t,0.,-1.],[t,0.,1.],[-t,0.,-1.],[-t,0.,1.]]
    vertices=[v/norm(v) for v in vertices]
    faces=[(1,12,6),(1,6,2),(1,2,8),(1,8,11),(1,11,12),
           (2,6,10),(6,12,5),(12,11,3),(11,8,7),(8,2,9),
           (4,10,5),(4,5,3),(4,3,7),(4,7,9),(4,9,10),
           (5,10,6),(3,5,12),(7,3,11),(9,7,8),(10,9,2)]
    for refinement in 1:level
        cache=Dict{Tuple{Int,Int},Int}();next=NTuple{3,Int}[]
        midpoint(a,b)=get!(cache,minmax(a,b)) do
            v=vertices[a]+vertices[b];push!(vertices,v/norm(v));length(vertices)
        end
        for (a,b,c) in faces
            ab,bc,ca=midpoint(a,b),midpoint(b,c),midpoint(c,a)
            append!(next,[(a,ab,ca),(b,bc,ab),(c,ca,bc),(ab,bc,ca)])
        end
        faces=next
    end
    mesh=Meshes.SimpleMesh([Meshes.Point(Tuple(v)) for v in vertices],
                           [Meshes.connect(f,Meshes.Triangle) for f in faces])
    return pnl.gt.GridTriangleSurface(mesh)
end

function validate(output)
    ispath(output) && error("Existing validation preserved: $output")
    results=Dict[]
    for level in 1:4
        body=pnl.RigidWakeBody{pnl.VortexRing,2}(sphere(level),zeros(Int,6,0);CPoffset=1e-14)
        normals=pnl.calc_normals(body);centers=pnl.calc_controlpoints(body,normals)
        @assert all(vec(sum(normals.*centers;dims=1)).>0)
        pnl.solve(body,repeat([1.,0.,0.],1,body.ncells),zeros(3,0),zeros(3,0);solver=solve_memory_bounded!)
        principal=pnl.calcfield_U(body,body)
        condition=least_squares_gradient!(body)
        pnl.addfields(body,"Ugradmu","U")
        cp=topology_pressure!(body,1.)
        radial=centers./sqrt.(sum(centers.^2;dims=1))
        exact=vec(1 .- 2.25.*(1 .- radial[1,:].^2))
        rms=sqrt(sum(abs2,cp-exact)/length(cp))
        push!(results,Dict("panels"=>body.ncells,"Cp_RMS_error"=>rms,
              "Cp_max_error"=>maximum(abs.(cp-exact)),"Cp_min"=>minimum(cp),
              "normal_velocity_rms"=>sqrt(sum(abs2,sum(principal.*normals;dims=1))/body.ncells),
              "gradient_condition_max"=>condition))
        println(last(results));flush(stdout);GC.gc()
    end
    errors=[r["Cp_RMS_error"] for r in results]
    passed=all(diff(errors).<0) && last(errors)<.05
    mkpath(dirname(output))
    open(output,"w") do io
        TOML.print(io,Dict("cases"=>results,"passed"=>passed,"RMS_limit"=>.05,
                          "analytic_Cp"=>"1 - 2.25 sin(theta)^2"))
    end
    @assert passed "Sphere pressure validation failed; do not infer wing pressure accuracy"
end

length(ARGS)==1 || error("Usage: validate_sphere.jl OUTPUT.toml")
validate(abspath(ARGS[1]))
