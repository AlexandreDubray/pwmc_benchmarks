import os
from yaml import load, Loader
import random
import math
random.seed(7552498)

_script_dir = os.path.dirname(os.path.realpath(__file__))

def has_path(source, target, edges):
    visited = set()
    q = list()
    q.append(source)
    while not len(q) == 0:
        node = q.pop()
        if node == target:
            return True
        visited.add(node)
        for (to, _) in edges[node]:
            if to not in visited:
                q.append(to)
    return False

def parse_file(filename):
    with open(os.path.join(_script_dir, filename), 'rb') as f:
        network = load(f, Loader=Loader)

    nodes = [x["name"] for x in network['nodes']]
    edges = {node: [] for node in nodes}
    sources = {x for x in nodes}
    targets = {x for x in nodes}
    for edge in network['links']:
        source = edge['start_node_name']
        target = edge['end_node_name']
        if target in sources:
            sources.remove(target)
        if source in targets:
            targets.remove(source)
        proba_up = random.random()
        edges[source].append((target, proba_up))

    return (nodes, edges, sources, targets)

files = ['Net1.json', 'Net2.json', 'Net3.json', 'Net6.json']

def pcnf_encoding(nodes, sources, targets, edges, network):
    clauses = []
    weights = []
    current_id = 1
    map_edge_id = {}
    for node in edges:
        for (to, proba) in edges[node]:
            weights.append(f'c p weight {current_id} {proba} 0')
            weights.append(f'c p weight -{current_id} {1.0 - proba} 0')
            map_edge_id[(node, to)] = current_id
            current_id += 1

    projected_header = f'c p show {" ".join([str(x) for x in range(1, current_id)])} 0'

    map_node_id = {}
    for node in nodes:
        map_node_id[node] = current_id
        current_id += 1

    for node in edges:
        for (to, _) in edges[node]:
            src_id = map_node_id[node]
            to_id = map_node_id[to]
            edge_id = map_edge_id[(node, to)]
            clauses.append(f'-{src_id} -{edge_id} {to_id} 0')

    for source in sources:
        for target in targets:
            if has_path(source, target, edges):
                with open(os.path.join(_script_dir, 'pcnf', network, f'{source}_{target}.cnf'), 'w') as f:
                    f.write(f'p cnf {current_id} {len(clauses) + 2}\n')
                    f.write(projected_header + '\n')
                    f.write('\n'.join(weights) + '\n')
                    f.write('\n'.join(clauses) + '\n')
                    f.write(f'{map_node_id[source]} 0\n')
                    f.write(f'-{map_node_id[target]} 0')

def sch_encoding(nodes, sources, targets, edges, network):
    distributions = []
    clauses = []
    current_id = 1
    map_edge_id = {}
    for node in edges:
        for (to, proba) in edges[node]:
            distributions.append(f'c p distribution {proba} {1.0 - proba}')
            map_edge_id[(node, to)] = current_id
            current_id += 2

    map_node_id = {}
    for node in nodes:
        map_node_id[node] = current_id
        current_id += 1

    for node in edges:
        for (to, _) in edges[node]:
            src_id = map_node_id[node]
            to_id = map_node_id[to]
            edge_id = map_edge_id[(node, to)]
            clauses.append(f'-{src_id} -{edge_id} {to_id} 0')

    for source in sources:
        for target in targets:
            if has_path(source, target, edges):
                with open(os.path.join(_script_dir, 'sch', network, f'{source}_{target}.cnf'), 'w') as f:
                    f.write(f'p cnf {current_id} {len(clauses) + 2}\n')
                    f.write('\n'.join(distributions) + '\n')
                    f.write('\n'.join(clauses) + '\n')
                    f.write(f'{map_node_id[source]} 0\n')
                    f.write(f'-{map_node_id[target]} 0')

def pl_encoding(nodes, sources, targets, edges, network):
    clauses = []
    for node in edges:
        for (to, proba) in edges[node]:
            clauses.append(f'{proba}::edge({node},{to}).')

    for source in sources:
        for target in targets:
            if has_path(source, target, edges):
                with open(os.path.join(_script_dir, 'pl', network, f'{source}_{target}.pl'), 'w') as f:
                    f.write('\n'.join(clauses) + '\n')
                    f.write('path(X, Y) :- edge(X, Y).\n')
                    f.write('path(X, Y) :- edge(X, Z), path(Z, Y).\n')
                    f.write(f'query(path({source},{target})).')

for filename in files:
    print(f"Handling {filename}")
    network = filename.split('.')[0]
    ppidimacs_dir = os.path.join(_script_dir, 'sch', network)
    pcnf_dir = os.path.join(_script_dir, 'pcnf', network)
    pl_dir = os.path.join(_script_dir, 'pl', network)
    os.makedirs(ppidimacs_dir, exist_ok=True)
    os.makedirs(pcnf_dir, exist_ok=True)
    os.makedirs(pl_dir, exist_ok=True)
    (nodes, edges, sources, targets) = parse_file(filename)
    print("\tpcnf")
    pcnf_encoding(nodes, sources, targets, edges, network)
    print("\tsch")
    sch_encoding(nodes, sources, targets, edges, network)
    print("\tpl")
    pl_encoding(nodes, sources, targets, edges, network)
