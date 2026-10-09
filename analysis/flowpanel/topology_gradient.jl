# FLOWPanel's default force_cellTE stencil assumes a structured cell ordering.
# For arbitrary meshes, select the TE one-ring by connectivity, never ci +/- 1.
function topology_gradient!(body)
    grid = body.grid
    te_nodes = Set{Int}()
    for (pi,ia,ib,pj,ja,jb) in eachcol(body.shedding)
        panel = pnl.gt.get_cell(grid,pi)
        push!(te_nodes,panel[ia],panel[ib])
        if pj > 0
            partner = pnl.gt.get_cell(grid,pj)
            @assert panel[ia] == partner[jb] && panel[ib] == partner[ja]
        end
    end
    gradient = pnl.calcfield_Ugradmu(body;force_cellTE=false,addfield=false)
    cell_gradient = pnl.calcfield_Ugradmu_cell(body;addfield=false)
    selected = Int[]
    for ci in 1:body.ncells
        if any(node in te_nodes for node in pnl.gt.get_cell(grid,ci))
            gradient[:,ci] .= cell_gradient[:,ci]
            push!(selected,ci)
        end
    end
    @assert all(isfinite,gradient)
    pnl.add_field(body,"Ugradmu","vector",eachcol(gradient),"cell")
    return length(selected)
end

# Kutta pressure correction on the actual paired TE panels only. FLOWPanel's
# built-in pi+1/pj-1 correction is not valid on arbitrary cell orderings.
function topology_pressure!(body,speed)
    cp = pnl.calcfield_Cp(body,speed;correct_kuttacondition=false,addfield=false)
    original = copy(cp)
    for (pi,ia,ib,pj,ja,jb) in eachcol(body.shedding)
        if pj > 0
            cp[pi] = cp[pj] = (original[pi]+original[pj])/2
        end
    end
    pnl.add_field(body,"Cp","scalar",cp,"cell")
    return cp
end

function least_squares_gradient!(body)
    grid=body.grid
    centers=pnl.calc_controlpoints(body,pnl.calc_normals(body))
    normals=pnl.calc_normals(body)
    cells=[collect(pnl.gt.get_cell(grid,i)) for i in 1:body.ncells]
    edges=Dict{Tuple{Int,Int},Vector{Int}}()
    cut=Set{Tuple{Int,Int}}()
    for (pi,ia,ib,pj,ja,jb) in eachcol(body.shedding)
        push!(cut,minmax(cells[pi][ia],cells[pi][ib]))
    end
    adjacent=[Int[] for _ in 1:body.ncells]
    for (i,tri) in enumerate(cells),j in 1:3
        push!(get!(edges,minmax(tri[j],tri[j%3+1]),Int[]),i)
    end
    for (edge,neighbors) in edges
        @assert length(neighbors)<=2
        if length(neighbors)==2 && !(edge in cut)
            i,j=neighbors;push!(adjacent[i],j);push!(adjacent[j],i)
        end
    end
    gradient=zeros(3,body.ncells);gamma=view(body.strength,:,1)
    maxcondition=0.
    for i in 1:body.ncells
        seen=Set([i]);frontier=Set([i])
        for ring in 1:2
            following=Set(j for k in frontier for j in adjacent[k]
                          if !(j in seen) && dot(normals[:,j],normals[:,i])>.5)
            union!(seen,following);frontier=following
        end
        neighbors=sort!(collect(setdiff(seen,Set([i]))))
        @assert length(neighbors)>=2
        tangent=grid._nodes[:,cells[i][2]]-grid._nodes[:,cells[i][1]]
        tangent/=norm(tangent);bitangent=cross(normals[:,i],tangent)
        delta=centers[:,neighbors].-centers[:,i]
        design=hcat(vec(tangent'*delta),vec(bitangent'*delta))
        scale=sqrt.(sum(design.^2;dims=1)./length(neighbors))
        @assert minimum(scale)>1e-15
        weight=1 ./ vec(sqrt.(sum(delta.^2;dims=1)))
        matrix=(design./scale).*weight
        singular=svdvals(matrix)
        @assert minimum(singular)>maximum(singular)*1e-12
        maxcondition=max(maxcondition,singular[1]/singular[end])
        slope=(matrix\((gamma[neighbors].-gamma[i]).*weight))./vec(scale)
        gradient[:,i] .= -.5*sign(body.CPoffset)*(slope[1]*tangent+slope[2]*bitangent)
    end
    @assert all(isfinite,gradient)
    pnl.add_field(body,"Ugradmu","vector",eachcol(gradient),"cell")
    return maxcondition
end
