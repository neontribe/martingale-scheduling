import pymatching

# Build a simple graph
m = pymatching.Matching()
m.add_edge(0, 1, weight=1.0)
m.add_edge(1, 2, weight=2.0)
m.add_edge(2, 3, weight=1.0)
m.add_edge(0, 3, weight=2.0)

# Syndrome: all 4 nodes
syndrome = [1, 1, 1, 1]

# Get matched pairs
matched_pairs = m.decode_to_matched_dets_array(syndrome)

print("Matched pairs:")
for u, v in matched_pairs:
    print(f"{u} <-> {v}")
