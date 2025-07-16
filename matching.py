import pymatching
import random
import time

#The first part of this is just generating a random undirected weighted graph of the form and scale needed for the problem

############################################################################################
#generates graph
m = pymatching.Matching()
added_edges = set() #this keeps track of the edges that are added

#assuming 140 candidates to interview
U = [i for i in range(140)]

#assuming 300 interview slots
V = [j for j in range(140,440)]

#the "add boundary" means that if necessary, these nodes (the interview slots) can be unmatched. 
#there are no boundaries on the candidate nodes, ensuring they are matched (if there is a solution)
for j in range(140,440):
    m.add_boundary_edge(j)

print("The nodes have been generated")

#only add edge to graph if it doesn't already exist
def add_edge_if_not_exists(matching, u, v, weight=1.0):
    edge = tuple(sorted((u, v)))  # Ensure undirected consistency
    if edge not in added_edges:
        matching.add_edge(u, v, weight=weight)
        added_edges.add(edge)

# Randomly generate edges between U and V
for k in range(len(U)):
    edges_per_node = random.randint(1,15)
    u = U[k]
    for l in range (edges_per_node):
        v = random.choice(V)
        weight = random.randint(0, 100)  # random weight - will be replaced with weights corresponding to travel costs 
        add_edge_if_not_exists(m,u,v, weight=weight)

print("The graph has been generated")
syndrome = [1 for n in range (len(U)+len(V))]
#the syndrome is a quantum error correction term. 
# In this context it just means the nodes which we want to include in the matching problem
# It accepts binary input, so 1 for every node means that all of the nodes are included

##########################################################################################
#Now actually matching the candidates to interview slots

start = time.time()
# Get matched pairs
#this outputs to an np array, but there are a range of other outputs possible using different methods
matched_pairs = m.decode_to_matched_dets_array(syndrome)
end = time.time()

print(f"Time to generate matching is {end-start}")

print("Matched pairs:")
for u, v in matched_pairs:
    print(f"{u} <-> {v}")

