'''
Copyright (C) Saeed Gholami Shahbandi. All rights reserved.
Author: Saeed Gholami Shahbandi (saeed.gh.sh@gmail.com)

This file is part of Subdivision Library.
The of Subdivision Library is free software: you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public License as published
by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along
with this program. If not, see <http://www.gnu.org/licenses/>
'''

import sys
if sys.version_info[0] == 3:
    from importlib import reload
elif sys.version_info[0] == 2:
    pass

import re
import yaml
import sympy as sym
import numpy as np
import skimage.transform
import matplotlib.path as mpath

from . import geometricTraits as trts
from . import arrangement as arr
# reload(trts)

################################################################################
################################################################################
################################################################################


################################################################################
def merge_faces_on_fly(arrangement, f1_idx, f2_idx):
    '''
    Note: this is still not a complete solution.
    If the merging of face create a holes, which [almost certainly] will happen
    if share mutual halfedge in places topologically distinct, the list of
    halfedges will contain more than one disjoint pathes.
    If there is more than one path, one chain of halfedge list will complete
    and eventhough the bank is not empty,it can not find a successor to the
    last halfedge.
    The raise will avoid infinite loop, but obviously it fails!
    For now I return None in such cases, but should find a smarter solution
    '''

    f1 = arrangement.decomposition.faces[f1_idx]
    f2 = arrangement.decomposition.faces[f2_idx]

    # finding mutual_halfedge (mut_he), all_halfedge (all_he)
    # and creating a bank of halfedges that contains all halfedges from both
    # faces, except for the halfedge in the mutual_halfedge 
    mut_he = arrangement.decomposition.find_mutual_halfEdges(f1_idx,f2_idx)
    all_he = f1.halfEdges + f2.halfEdges
    bank = [he for he in all_he if he not in mut_he]

    if len(mut_he)==0:
        # just in case if I forget to check faces' neighborhood before calling
        # this method
        return None

    # creating a new list of halfedges (new_he), in correct order
    new_he = [bank.pop(0)]
    while len(bank)>0:
        
        # find the successor halfedge
        # to the last item in the last sequence of new_he
        next_node_idx = new_he[-1][1]
        next_idx = [idx for idx,he in enumerate(bank) if he[0] == next_node_idx]

        if len(next_idx)==0:
            return None
            raise( NameError( 'there are disjoint chains of halfedges' ) )
            # probably [almost certainly] only one chain is the face and the
            # rest are holes

        elif len(next_idx)==1:
            # still in the same path, proceed
            next_idx = next_idx[0]
            new_he.append( bank.pop(next_idx) )

        elif len(next_idx) >1:
            # raise( NameError( 'more than one halfedge to follow...' ) )
            
            # e.g. concentric squares connected with a pair of twin halfedges
            # e.g. a polygon inside another polygon, sharing one node  
            # the following will take care of the first example 
            
            # print ('have to discard pairs of twin halfedges')
            twins_idx_in_bank = [idx
                                 for idx, (s,e,k) in enumerate(bank)
                                 if arrangement.graph[s][e][k]['obj'].twinIdx in bank]
            twins_idx_in_bank.sort(reverse=True)
            for idx in twins_idx_in_bank:
                bank.pop(idx)
            
    # creating a path from the new list of halfedges
    new_path = edgeList_2_mplPath(new_he, arrangement.graph, arrangement.traits )

    # creating and returning a Face instance for the merged face
    return arr.Face(new_he, new_path)

################################### converting face to mpl.path
def edgeList_2_mplPath (edgeList, graph, traits):
    '''
    important note:
    this works only if the edgeList is sorted
    and the sequence of edges shall represent a simple closed trait (path)
    '''
    
    # step1: initialization - openning the path
    (start, end, k) = edgeList[0]
    p = graph.node[start]['obj'].point
    x, y = p.x.evalf(), p.y.evalf()
    
    verts = [ (x,y) ]
    codes = [ mpath.Path.MOVETO ]

    # step2: construction - by following the trajectory of edges in edgeList
    for halfEdge in edgeList:

        (start, end, k) = halfEdge
        halfEdge_obj = graph[start][end][k]['obj']
        cIdx = halfEdge_obj.traitIdx
        sTVal, eTVal = halfEdge_obj.get_tvals(traits, graph.node)

        if isinstance(traits[cIdx].obj, ( sym.Line, sym.Segment, sym.Ray) ):
            p2 = graph.node[end]['obj'].point
            x, y = p2.x.evalf(), p2.y.evalf()
            verts.append( (x,y) )
            codes.append( mpath.Path.LINETO )

        elif isinstance(traits[cIdx].obj, sym.Circle):
            circ = traits[cIdx].obj
            xc, yc, rc = circ.center.x , circ.center.y , circ.radius
            
            # create an arc 
            t1 = np.float(sTVal) *(180 /np.pi)
            t2 = np.float(eTVal) *(180 /np.pi)

            if halfEdge_obj.direction == 'negative':
                # TODO(saesha): which one?
                arc = mpath.Path.arc( t2,t1 )
                # arc = mpath.Path.arc( np.min([t1,t2]), np.max([t1,t2]) )
            else:
                arc = mpath.Path.arc( t1,t2 )

            # transform arc
            transMat = matplotlib.transforms.Affine2D( )
            ## Note that the order of adding rot_scale_translate matters
            transMat.rotate(0) # rotate_around(x, y, theta)
            transMat.scale( rc ) # scale(sx, sy=None)
            transMat.translate(xc, yc) 
            arc = arc.transformed(transMat)
            
            vs = list( arc.vertices.copy() )
            cs = list( arc.codes.copy() )
            # which one? cs[0] = mpath.Path.MOVETO or mpath.Path.LINETO
            # Lineto, because, otherwise, decompsong the face into polygones
            # for area approximation, it will result in disjoint segments
            cs[0] = mpath.Path.LINETO
            
            # reversing the order of vertices, if the halfEdge has negative direction
            if halfEdge_obj.direction == 'negative': vs.reverse()

            verts.extend( vs )
            codes.extend( cs )

    assert len(verts) == len(codes)

    # step3: finialize - closing the path
    # making sure that the last point of the path is not a control point of an arc
    if codes[-1] == 4:
        (start, end, k) = edgeList[0]
        p = graph.node[start]['obj'].point
        x, y = np.float(p.x.evalf()), np.float(p.y.evalf())
        verts.append( (x,y) )
        codes.append( mpath.Path.CLOSEPOLY )
    else:
        codes[-1] = mpath.Path.CLOSEPOLY 
        
    return mpath.Path(verts, codes)

################################################################################
def load_data_from_yaml(fileName=None):

    Point = sym.Point
    Line = trts.LineModified
    Ray = trts.RayModified
    Segment = trts.SegmentModified
    Circle = trts.CircleModified
    Arc = trts.ArcModified

    result = {}
    traits = []

    if 'random' in fileName: # generate an almost random case 

        result.update( {'dataset': 'random'} )

        nl = 4
        X1 = np.random.random(nl)
        Y1 = np.random.random(nl)
        X2 = np.random.random(nl)
        Y2 = np.random.random(nl)
        traits += [ Line( args=(Point(x1,y1), Point(x2,y2)) )
                   for (x1,y1,x2,y2) in zip(X1,Y1,X2,Y2) ]

        nc = 2
        Xc = np.random.random(nc)
        Yc = np.random.random(nc)
        Rc = np.random.random(nc) + .75
        traits += [ Circle( args=(Point(xc,yc), rc) )
                   for (xc,yc,rc) in zip(Xc,Yc,Rc) ]



    elif 'star' in fileName:

        result.update( {'dataset': 'star'} )

        # generate the star case
        # happens to be very tricky
        a1 = 36 * np.pi/180
        a2 = 72 * np.pi/180
        p1 = Point(-np.sqrt(1 - np.cos(a1)**2 ), np.cos(a1))
        p2 = Point(+np.sqrt(1 - np.cos(a1)**2 ), np.cos(a1))
        p3 = Point(0, -1)
        traits = [ Line( args=(p1, 0) ),
                   Line( args=(p3, -np.tan(a1)) ),
                   Line( args=(p3, +np.tan(a1)) ),
                   Line( args=(p1, +np.tan(a2)) ),
                   Line( args=(p2, -np.tan(a2)) ),
                   Circle( args=(Point(0,0), np.cos(a1)) ),
                   Circle( args=(Point(0,0), 1) ),
                   Circle( args=(Point(0,0), 2) ) ]        

        result.update( {'number_of_nodes': 25} )
        result.update( {'number_of_edges': 100} )
        result.update( {'number_of_faces': 26} )
        result.update( {'number_of_subGraphs': 1} )       

    else: 

        stream = open(fileName, 'r')
        data = yaml.load(stream)

        if 'dataset' in data.keys():
            result.update( {'dataset': data['dataset']} )

        if 'testValues' in data.keys():
            result.update( data['testValues'][0] )

        if 'lines' in data.keys():
            for l in data['lines']:
                if len(l) == 4: #[x1,y1,x2,y2]
                    traits += [ Line( args=(Point(l[0],l[1]), Point(l[2],l[3]))) ]
                elif len(l) == 3: #[x1,y1,slope]
                    traits += [ Line( args=(Point(l[0],l[1]), l[2])) ]

        if 'segments' in data.keys():
            for s in data['segments']:
                seg = Segment( args=(Point(s[0],s[1]), Point(s[2],s[3])))
                if isinstance(seg.obj, sym.Segment): # not(isinstance(seg.obj, sym.Point))
                    traits += [ seg ]

        if 'rays' in data.keys():
            for r in data['rays']:
                traits += [ Ray( args=(Point(r[0],r[1]), Point(r[2],r[3]))) ]


        if 'circles' in data.keys():
            for c in data['circles']:
                traits += [ Circle( args=(Point(c[0],c[1]), c[2]) ) ]

        if 'arcs' in data.keys():
            for a in data['arcs']:
                traits += [ Arc( args=( Point(a[0],a[1]), a[2], (a[3],a[4])) ) ]
                
        if 'boundary' in data.keys():
            result.update( {'boundary':  data['boundary']} )
        else:
            print ('\t WARNING boundary info not available in yaml WARNING ')

    result.update( {'traits': traits} )

    return result

################################################################################
def unbound_traits(trait_list):
    '''
    this method takes a list of traits and converts them as follow:
    ray -> line
    segment -> line
    line -> line
    arc -> circle
    circle -> circle
    '''

    for idx in range(len(trait_list)):

        # the trait before adjustment
        trait = trait_list[idx]
        
        if isinstance(trait, (trts.SegmentModified, trts.RayModified) ):
            # if the trait is (ray v segment) convert to line 
            trait = trts.LineModified( args=(trait.obj.p1,
                                             trait.obj.p2) )
            
        elif isinstance(trait, trts.ArcModified):
            # if the trait is (arc) convert to circle
            trait = trts.Circle( args=(trait.obj.center,
                                       trait.obj.radius) )
        
        else:
            # the trait is either line or circle
            # no need to adjust the trait
            pass

        # insertig the corrected trait back in the list
        trait_list[idx] = trait

    return trait_list

################################################################################
def bound_traits(trait_list, boundary):
    '''
    this method takes a list of traits and bounds them to boundary.
    line -> segment

    note:
    it only supports boundary [xMin, yMin, xMax, yMax] form. this means,
    the region of interest (ROI) is always rectangle (parallel to x/y axes)
    it could be extended to support any kind of region of interest by define
    the region with a path (e.g. matplotlib) and check if the intersection
    points are in bound.
    Since I don't need that genralization, I stick to this simple version
    '''
    xMin, yMin, xMax, yMax = boundary

    b_lines  = [ sym.Line( (xMin,yMin), (xMax,yMin) ),
                 sym.Line( (xMax,yMin), (xMax,yMax) ),
                 sym.Line( (xMax,yMax), (xMin,yMax) ),
                 sym.Line( (xMin,yMax), (xMin,yMin) ) ]



    for t_idx in range(len(trait_list)-1,-1,-1):

        # the trait before adjustment
        trait = trait_list[t_idx]
        
        if isinstance(trait, (trts.LineModified) ):            

            # finding all intersections between trait and boundary lines
            # the "if" condition is to reject lines:
            # sym.intersection would return a sym.Line if one of the traits
            # is the same as one of the boundary lines
            points = [ p
                       for b_line in b_lines
                       for p in sym.intersection( trait.obj, b_line )
                       if isinstance(p, sym.Point)]

            for p_idx in range(len(points)-1,-1,-1):
                # checking which points are out of bound wrt. RIO
                inbound_x = (xMin <= points[p_idx].x <= xMax)
                inbound_y = (yMin <= points[p_idx].y <= yMax)
                if not(inbound_x) or not(inbound_y):
                    points.pop(p_idx)
            
            if len(points)>2:
                # this means some points are coinciding on one corner
                for p_idx_1 in range(len(points)-1,-1,-1):
                    for p_idx_2 in range(p_idx_1): 
                        if points[p_idx_1].distance(points[p_idx_2])<np.spacing(10**10):
                            points.pop(p_idx_1)
                            break

            if len(points) == 2:
                # in case a trait does not pass through the RIO
                # insertig the corrected trait back in the list
                trait = trts.SegmentModified( args=(points[0],points[1]) )
                trait_list[t_idx] = trait
            else:
                trait_list.pop(t_idx)

        else:
            # the trait is either arc or circle
            # no need to adjust the trait
            pass

    return trait_list

################################################################################
def get_shape_descriptor(face, arrangement, 
                         remove_redundant_lines=True):
    '''
    This method returns a descriptor for the shape of the input face:
    
    usage
    -----
    (edge_type, edge_turn, edge_start_node_idx) = get_shape_descriptor(face, arrangement)
    
    input
    -----
    face: index to target face of the arrangment 
    arrangement: an instance of arrangement.arrangement
    
    Parameter
    ---------
    The parameter "remove_redundant_lines" removes straight lines that:
    > follow another line, and do turn wrt previous line
    
    output
    ------
    it returns the following varibles
    The descriptor is defined by on ordered sequenced of edges:
    > edge_type (string) - the edge type
    > edge_turn (np.array) - the turning angle of the edge at the begining,
    > edge_node_idx (list) - the starting point of the edge
    
    Note
    ----
    A face is identified by indices to half-edges that bounds it.
    Therefore, the arrangement object, to which face belong is required for:
    > accessing the objects of half-edges, nodes and traits that define a face.
    '''
    # area = face.get_area()
    
    # get the idx:(start,end,key) of all halfedges surrounding the face
    # note that this list includes the outer half_edges of the holes
    all_halfedges_idx = face.get_all_halfEdges_Idx()
    
    # remove half_edges belonging to the holes
    holes_halfedges_idx = []
    for hole in face.holes:        
        holes_halfedges_idx.append( hole.get_all_halfEdges_Idx() ) 
        for (s,e,k) in holes_halfedges_idx[-1]:
            all_halfedges_idx.pop( all_halfedges_idx.index((s,e,k)) )

    # at this point:
    # all_halfedges_idx -> a list of face's half-edges, except for the holes
    # holes_halfedges_idx -> contians a list half-edge per each hole
    # --> for hole[0] -> halfedges_idx = holes_halfedges_idx[0] = [(s,e,k), ...]
    
    # check if the order of edges is correct
    # I'm pretty sure the half-edges must be in order, since decomposition point
    # unless the are altered somewhere, which is unlikely!
    for idx in range(len(all_halfedges_idx)):
        s = all_halfedges_idx[idx][0]
        e = all_halfedges_idx[idx-1][1]
        if s!=e:
            raise (NameError('half-edges are not in order... '))
                

    # enumerate over the list of half-edges and store their description
    edge_type = '' # types could be L:Line, or C:Circle
    edge_angle = [] # (ds,de) direction of the trait at start and end (radian)
    edge_node_idx = [] # index to STARTING node of the edge

    for (s,e,k) in all_halfedges_idx:
            
        half_edge = arrangement.graph[s][e][k]['obj']
        edge_node_idx += [s]
        
        # storing the type
        trait = arrangement.traits[ half_edge.traitIdx ]
        L = isinstance( trait.obj, (sym.Line, sym.Segment, sym.Ray) )
        C = isinstance( trait.obj, sym.Circle )
        edge_type += 'L' if L else 'C'
        
        # storing the direction ( angle )
        start_point = arrangement.graph.node[s]['obj'].point
        start_angle = trait.tangentAngle(start_point, half_edge.direction)
        end_point = arrangement.graph.node[e]['obj'].point
        end_angle = trait.tangentAngle(end_point, half_edge.direction)
        
        edge_angle += [(start_angle, end_angle)]
            
    # computing the turning angles of the edge at their starting node
    # turn[i] =  angle_end[i-1] - angle_start[i]
    starting_angles = np.array([s for (s,e) in edge_angle])
    ending_angles = np.array([e for (s,e) in edge_angle])
    ending_angles = np.roll(ending_angles, 1)
    
    # turn -> exterior angle
    # the following stuff fixes this: 
    # t2 = pi-epsilon,  t1 = -pi+epsilon
    # turn = -2x espilon, but t2-t1= 2x(pi-epsilon)
    
    # mvoing all the angle to [0,2pi]
    starting_angles = np.mod(starting_angles, 2*np.pi)
    ending_angles = np.mod(ending_angles, 2*np.pi)
    # moving the ending angles + and - 2*pi, to assure finding minimum distance
    sa = starting_angles
    ea = np.array([ending_angles ,
                   ending_angles +2*np.pi,
                   ending_angles -2*np.pi])
    
    edge_turn = list( np.min(np.abs(ea-sa),axis=0) )
    
    # dumping all Ls, that are followed by other Ls without a turn
    if remove_redundant_lines:
            
            # finding all matches,
        # by extending the edge_type with edge_type[0], we check tial-haed too
        regex, sub = edge_type+edge_type[0], 'LL'
        match_idx = np.array([ match.start()
                               for match in re.finditer('(?={:s})'.format(sub), regex) ])
        
        # match_idx shows indices to starting point of the pattern (i.e. first line)
        # we want to remove the line that follows another (i.e. second line)
        match_idx += 1 # getting the index of the second line
        match_idx = np.mod(match_idx, len(edge_type)) # bringing all indices in range
        
        # sortin indices in reverse order, for poping
        match_idx = list(match_idx)
        match_idx.sort(reverse=True)
        
        edge_turn = list(edge_turn)
        edge_type = list(edge_type)
        edge_node_idx = list(edge_node_idx)
        
        for idx in match_idx:
            # indexing with np.mod, in case a match happens at tail-head
            # for which we have to remove the first element!
            # but that will change 
            if edge_turn[idx] == 0:
                edge_turn.pop(idx)
                edge_type.pop(idx)
                edge_node_idx.pop(idx)

    assert len(edge_turn) == len(edge_type) == len(edge_node_idx)
    
    return edge_turn, edge_type, edge_node_idx

################################################################################
def match_face_shape(face1, face2,
                     include_angle=False):
    '''
    This method takes two faces and compares their shape.
    The comparison is a regex match by rolling (to left) the edge_type of the
    face1, and results a list of integers, each indicating steps of roll (to 
    left) that would match two faces.

    Input
    -----
    face1 (src), face2 (dst): instances of arrangement.face

    Parameter
    ---------
    include_angle: Boolean (default:False)
    Not functional yet!

    Output
    ------
    matches: list of integer
    the number of steps of roll to left that would match two faces
    
    Note
    ----
    If the sizes of edge_type2 and edge_type1 do not match this method would
    not return a match

    Note
    ----
    face1 and face2 do not belong to the same arrangement.
    since we don't need any information beyond face.attributes,
    no need to pass the arrangments.
    But the face attrribute['edge_type'] must be set before calling
    this method

    TODO:
    adopt the code to consider "include_angle"   
    '''

    # print (' TODO: adopt the code to consider "include_angle"')   
    match = []

    attr1 = face1.attributes
    attr2 = face2.attributes

    edge_type1 = attr1['edge_type']
    edge_type2 = attr2['edge_type']
    
    for roll in range(len(edge_type1)):
        # rolling to left
        # if the sizes of edge_type2 and edge_type1 do not match
        # this will never return a match
        if edge_type2 == edge_type1[roll:]+edge_type1[:roll]:
            match += [roll]

    return match


################################################################################
def align_faces(arrangement1, arrangement2,
                f1Idx, f2Idx,
                tform_type='similarity',
                enforce_match=False ):
    '''
    This method returns a list rigid transformation (+scale) that would aligne
    input faces.
    Matches from the "match_face_shape" method indicate rolling steps to the left.
    In numpy terms, it corresponds to np.roll(array, -roll_step, axis=0)

    Parameter
    ---------
    tform_type - {'similarity', 'affine', 'piecewise-affine', 'projective', 'polynomial'}
    types of transformation (default 'similarity')
    similarity: shape-preserving transformations
    affine: translation, scaling, homothety, reflection, rotation, shear mapping, and compositions
    see "print skimage.transform.estimate_transform.__doc__" for more details.

    Output
    ------
    alignments - dictionary
    Keys in the dictionary correspond to steps of rolls for match
    And the field to each key is the "GeometricTransform" object.
    see "print skimage.transform.estimate_transform.__doc__ for more details"

    Note
    ----
    src = face1 , dst = face2
    so the result is a transformation from face1 to face2    

    Note
    ----
    face1 and face2 do not belong to the same arrangement
    and since we need any node informations, we pass the arrangments too

    todo
    ----
    Could this happen? 
    make sure sx == sy and sx>0
    note that sx <0 could happen, indicating a mirror
    for instance two quadrant of a circle could be aligned with rotation or flip
    sx==sy holds true if 'similarity' is used
    '''

    alignments = {}

    f1 = arrangement1.decomposition.faces[f1Idx]
    f2 = arrangement2.decomposition.faces[f2Idx]

    nodes1 = arrangement1.graph.node
    nodes2 = arrangement2.graph.node
    
    src = np.array( [(nodes1[n_idx]['obj'].point.x,
                      nodes1[n_idx]['obj'].point.y)
                     for n_idx in f1.attributes['edge_node_idx'] ],
                    dtype=np.float)
    
    dst = np.array( [(nodes2[n_idx]['obj'].point.x,
                      nodes2[n_idx]['obj'].point.y)
                     for n_idx in f2.attributes['edge_node_idx'] ],
                    dtype=np.float)

    # abort if there isn't enough points
    if (src.shape[0]<3) or (dst.shape[0]<3):
        # if the number of veritices are less than 3, it is still possible to find a match
        # but no loger possible to estimate an alignment (needs at least 3 points)
        return alignment # returning an empty list

    if not(enforce_match):
        matches = match_face_shape(f1,f2)    

        for roll in matches:
            tform = skimage.transform.estimate_transform( tform_type,
                                                          np.roll(src,-roll,axis=0),
                                                          dst )
            # Note that the second value in key tuple is the roll of 
            # dst point. even though with "match" the roll for dst is always
            # zero, it is still set, for the sake of consistency with 
            # the "enforce_match" case
            alignments[(roll,0)] = tform

    elif enforce_match:
        # it's a very rough brute force manner that would skip match and
        # take all "3-consequtive nodes" from face1 and align them with all
        # "3-consequtive nodes" from face2... talking about rough, ha?
        
        src_len = src.shape[0]-1
        dst_len = dst.shape[0]-1

        src = np.concatenate((src,src[:2,:]))
        dst = np.concatenate((dst,dst[:2,:]))

        for src_idx in range(src_len):
            for dst_idx in range(dst_len):
                tform = skimage.transform.estimate_transform( tform_type,
                                                              src[src_idx:src_idx+3, :],
                                                              dst[dst_idx:dst_idx+3, :] )

                alignments[(src_idx,dst_idx)] = tform
    
    return alignments

