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

import subdivision as sdv
import plotting as myplt
import testCaseGenerator as tcg
reload(sdv)
reload(myplt)
reload(tcg)

# TODO(saesha) documentation

# TODO(saesha) testing 
# use suite() so it runs all tests, even if one fails

# TODO(saesha) bug "test case 2" fails
# two tangent circles one inside another are not standalone, but behave like one
# starting from the positive half-edge of the outer circle, the face will close
# with only one half-edge, ignoring the negative half-edge of the inner circle.
# that is because the condition of sNodeIdx == eNodeIdx will be satisfied.

# TODO(saesha) bug "test case 13" fails
# due to unknown

# TODO(saesha) bug-developement
# for hole in face.holes: assert len(hole.face.hole)==0

# TODO(saesha) developement
# Decomposition.find_neighbours(), and don't forget to include half-edges from holes.
# for this actually we need to make sure there is no redundancy in holes!


################################################################################
################################################################# initialization
################################################################################
test_cases_key = [
    'default',                      # 0: 
    'default_small',                # 1: 
    'specialCase_01',               # 2: 4 tangent circles and a line  # fails
    'specialCase_02',               # 3: non-interrsecting circle
    'specialCase_03',               # 4: single circle 4 intersections
    'specialCase_04',               # 5: 2 lines - one circle
    'specialCase_05',               # 6: a square - a circle
    'specialCase_06',               # 7: concentric circles
    'specialCase_07',               # 8: disjoint
    'specialCase_08',               # 9: 2 pairs of tangent circles
    'intensive',                    # 10: 
    'intensive_x2',                 # 11:
    'intensive_lineOnly',           # 12:
    'random',                       # 13:
    'star',                         # 14: 
    'example_01'                    # 15: 2 circles and a line
]

########################################
file_name = 'testCases/'+test_cases_key[1]+'.yaml'
data = tcg.load_from_csv( file_name )
curves = data['curves']

if 'number_of_nodes' in data.keys(): # len(data.keys()) > 1
    testing = True
    n_nodes = data['number_of_nodes']
    n_edges = data['number_of_edges']
    n_faces = data['number_of_faces']
    n_subGraphs = data['number_of_subGraphs']
else:
    testing = False

################################################################################
###################################### deploying subdivision (and decomposition)
################################################################################
print 'start decomposition'
mySubdivision = sdv.Subdivision(curves, multiProcessing=4)

if testing:
    cond =[]
    cond += [ len(mySubdivision.MDG.nodes()) == n_nodes ]
    cond += [ len(mySubdivision.MDG.edges()) == n_edges ]
    cond += [ len(mySubdivision.decomposition.faces) == n_faces ]
    cond += [ len(mySubdivision.subGraphs) == n_subGraphs ]
    print 'success' if all(cond) else 'fail'

    print 'nodes:\t\t', len(mySubdivision.MDG.nodes()), '\t expected:', n_nodes
    print 'edges:\t\t', len(mySubdivision.MDG.edges()), '\t expected:', n_edges
    print 'faces:\t\t', len(mySubdivision.decomposition.faces), '\t expected:', n_faces
    print 'subGraphs:\t', len(mySubdivision.subGraphs), '\t expected:', n_subGraphs

elif not(testing):
    print 'nodes:\t\t', len(mySubdivision.MDG.nodes())
    print 'edges:\t\t', len(mySubdivision.MDG.edges())
    print 'faces:\t\t', len(mySubdivision.decomposition.faces)
    print 'subGraphs:\t', len(mySubdivision.subGraphs)

################################################################################
####################################################################### plotting
################################################################################
# myplt.plot_graph(mySubdivision.MDG)
# myplt.plot_decomposition_colored(mySubdivision,
#                                  printNodeLabels=False,
#                                  printEdgeLabels=False)
myplt.plot_decomposition(mySubdivision,
                         interactive_onClick=False,
                         interactive_onMove=False,
                         plotNodes=True, printNodeLabels=False,
                         plotEdges=True, printEdgeLabels=True)

################################################################################
###################################################################### animating
################################################################################
myplt.animate_face_patches(mySubdivision, timeInterval = .1*1000)
# myplt.animate_halfEdges(mySubdivision, timeInterval = 1.5*1000)


################################################################################
####################################################################### API demo
################################################################################
# Subdivision
# Decomposition
# Curve
# Node
# HalfEdge
# Face



# print 'checking twin assignment'
# for idx in mySubdivision.get_all_HalfEdge_indices():
#     (s,e,k) = idx
#     # side = mySubdivision.MDG[s][e][k]['obj'].side
#     tidx = mySubdivision.MDG[s][e][k]['obj'].twinIdx
#     (ts,te,tk) = tidx

#     ttidx = mySubdivision.MDG[ts][te][tk]['obj'].twinIdx
    
#     if idx != ttidx:
#         print 'oops'
