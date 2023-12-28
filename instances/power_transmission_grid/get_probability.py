import os
import sys
import re
import itertools
from operator import mul
_script_dir = os.path.dirname(os.path.realpath(__file__))

def get_graph(filename):
    distributions = []
    # First parse the distributions
    with open(os.path.join(_script_dir, filename)) as f:
        for line in f:
            if line.startswith('c p distribution'):
                distribution = [float(x) for x in line.rstrip().split(' ')[3:]]
                distributions.append(distribution)

    # Parse the graph structure from the clauses
    with open(os.path.join(_script_dir, filename)) as f:
        nodes = {}
        source = None
        target = None
        first = True
        for line in f:
            if first or line.startswith('c'):
                first = False
                continue
            ls = line.rstrip().split(' ')[:-1]
            if len(ls) != 3:
                if line.startswith('-'):
                    target = int(ls[0][1:])
                else:
                    source = int(ls[0])
                continue
            s = [int(re.sub('-', '', x)) for x in line.rstrip().split(' ')[:-1]]
            d_id = int((s[1] - 1) / 2)
            nfrom = s[0]
            nto = s[2]
            p_edge = distributions[d_id][0]
            try:
                nodes[nfrom].add((nto, p_edge))
            except KeyError:
                nodes[nfrom] = {(nto, p_edge)}
            try:
                nodes[nto].add((nfrom, p_edge))
            except KeyError:
                nodes[nto] = {(nfrom, p_edge)}
        return nodes, source, target

def find_all_path_(nodes, source, target, visited, paths_cache):
    if source in paths_cache:
        return paths_cache[source]
    if source not in nodes:
        return []
    visited.add(source)
    paths = []
    try:
        for (n, proba) in nodes[source]:
            low = n if source > n else source
            high = n if low == source else source
            if n == target:
                paths.append([(low, high, proba)])
                continue
            if n not in visited:
                paths += [[(low, high, proba)] + p for p in find_all_path_(nodes, n, target, visited, paths_cache)]
    except KeyError:
        pass
    paths_cache[source] = paths
    visited.remove(source)
    return paths

def find_all_path(nodes, source, target):
    return find_all_path_(nodes, source, target, set(), {})

def get_path_proba(p):
    proba = 1.0
    for (_,_, x) in p:
        proba *= x
    return proba

g, source, target = get_graph(sys.argv[1])
paths = find_all_path(g, source, target)
proba = 0.0
for p in paths:
    print(p)
    proba += get_path_proba(p)
substract = True
indexes = [i for i in range(len(paths))]
for k in range(2, len(paths)+1):
    for combination in itertools.combinations(indexes, k):
        edges = set()
        for x in combination:
            edges = edges.union(set(paths[x]))
        proba_common = 1.0
        for e in edges:
            proba_common *= e[2]
        if substract:
            proba -= proba_common
        else:
            proba += proba_common
    substract = not substract
print(len(paths), 1.0 - proba)
