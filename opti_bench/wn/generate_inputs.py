import os
from yaml import load, Loader
import math
import queue

_script_dir = os.path.dirname(os.path.realpath(__file__))

def parse_file(filename):
    with open(os.path.join(_script_dir, '..', '..', 'instances', 'water-supply-network', filename), 'rb') as f:
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
        proba_up = 0.125
        edges[source].append((target, proba_up))

    return (nodes, edges, sources, targets)

def distances_from_source(edges, source):
    distances = {}
    q = queue.Queue()
    q.put((source, 0))
    while not q.empty():
        (node, dist) = q.get()
        if node in distances:
            continue
        distances[node] = dist
        for to, _, _ in edges[node]:
            if to not in distances:
                q.put((to, dist + 1))
    return distances
            

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
        for (to, _, _) in edges[node]:
            src_id = map_node_id[node]
            to_id = map_node_id[to]
            edge_id = map_edge_id[(node, to)]
            clauses.append(f'-{src_id} -{edge_id} {to_id} 0')

    for source in sources:
        source_dist = distances_from_source(edges, source)
        for target in targets:
            if has_path(source, target, edges):
                with open(os.path.join(_script_dir, 'sch', network, f'{source}_{target}.cnf'), 'w') as f:
                    f.write(f'p cnf {current_id} {len(clauses) + 2}\n')
                    f.write('\n'.join(distributions) + '\n')
                    f.write('\n'.join(clauses) + '\n')
                    f.write(f'{map_node_id[source]} 0\n')
                    f.write(f'-{map_node_id[target]} 0')

def pcnf_encoding(nodes, sources, targets, edges, network):
    clauses = []
    weights = []
    current_id = 1
    map_edge_id = {}
    for node in edges:
        for (to, proba, _) in edges[node]:
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
        for (to, _, _) in edges[node]:
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

def pl_encoding(nodes, sources, targets, edges, network):
    seen_edges = set()
    clauses = []
    counter_additional = 1
    map_node_id = {nodes[i]: i+1 for i in range(len(nodes))}
    for node in edges:
        for (to, proba) in edges[node]:
            edge = (node, to)
            n = map_node_id[node]
            t = map_node_id[to]
            if edge not in seen_edges:
                clauses.append(f'{proba}::edge({n},{t}).')
                seen_edges.add(edge)
            else:
                # We create 2 dummy nodes with probability 1 and then link them with the correct probability
                dummy_node = f'dummy_{n}_{t}_{counter_additional}'
                dummy_to = f'dummy_{t}_{n}_{counter_additional}'
                clauses.append(f'edge({n},{dummy_node}).')
                clauses.append(f'edge({t},{dummy_to}).')
                clauses.append(f'{proba}::edge({dummy_node},{dummy_to}).')
                counter_additional += 1

    for source in sources:
        for target in targets:
            if has_path(source, target, edges):
                with open(os.path.join(_script_dir, 'pl', network, f'{source}_{target}.pl'), 'w') as f:
                    f.write('\n'.join(clauses) + '\n')
                    f.write('path(X, Y) :- edge(X, Y).\n')
                    f.write('path(X, Y) :- edge(X, Z), path(Z, Y).\n')
                    f.write(f'query(path({map_node_id[source]},{map_node_id[target]})).')

def has_path(source, target, edges):
    visited = set()
    q = list()
    q.append(source)
    while not len(q) == 0:
        node = q.pop()
        if node == target:
            return True
        visited.add(node)
        for (to, _, _) in edges[node]:
            if to not in visited:
                q.append(to)
    return False

files = ['Net1.json', 'Net2.json', 'Net3.json', 'Net6.json']

for filename in files:
    print(f"Handling {filename}")
    network = filename.split('.')[0]
    os.makedirs(os.path.join(_script_dir, 'sch'), exist_ok=True)
    os.makedirs(os.path.join(_script_dir, 'pcnf'), exist_ok=True)
    os.makedirs(os.path.join(_script_dir, 'pl'), exist_ok=True)
    (nodes, edges, sources, targets) = parse_file(filename)
    print("\tpcnf")
    pcnf_encoding(nodes, sources, targets, edges, network)
    print("\tsch")
    sch_encoding(nodes, sources, targets, edges, network)
    print("\tpl")
    pl_encoding(nodes, sources, targets, edges, network)
