import os
from yaml import load, Loader
import random
import math
random.seed(7552498)

_script_dir = os.path.dirname(os.path.realpath(__file__))
ppidimacs_dir = os.path.join(_script_dir, 'schlandals')
pcnf_dir = os.path.join(_script_dir, 'pcnf')
os.makedirs(ppidimacs_dir, exist_ok=True)
os.makedirs(pcnf_dir, exist_ok=True)

def find_reachables(source, node_edges, visited):
    visited.add(source)
    try:
        for edge in node_edges[source]:
            target = edge['end_node_name']
            if target not in visited:
                find_reachables(target, node_edges, visited)
    except KeyError:
        pass

def find_used_edges(node, target, node_edges, max, cache, seen_nodes):
    if node in seen_nodes:
        return max
    seen_nodes.add(node)
    if node == target:
        return 0
    if node not in node_edges:
        return max
    dist = max
    for edge in node_edges[node]:
        if edge['name'] in cache:
            dist = min(dist, cache[edge['name']])
        else:
            to = edge['end_node_name']
            dist_edge = find_used_edges(to, target, node_edges, max, cache, seen_nodes)
            dist = min(dist, dist_edge)
            cache[edge['name']] = dist
    return dist

def parse_file(filename):
    with open(os.path.join(_script_dir, filename), 'rb') as f:
        network = load(f, Loader=Loader)
    nodes = network['nodes']
    edges = network['links']
    name = network['name'].split('.')[0]
    print(f'Network {name} with {len(nodes)} nodes and {len(edges)} edges')
    node_edges = {}
    for edge in edges:
        s = edge['start_node_name']
        try:
            node_edges[s].append(edge)
        except KeyError:
            node_edges[s] = [edge]
    
    sources = {node['name'] for node in nodes}
    targets = {node['name'] for node in nodes}
    for edge in edges:
        if edge['end_node_name'] in sources:
            sources.remove(edge['end_node_name'])
        if edge['start_node_name'] in targets:
            targets.remove(edge['start_node_name'])
    
    queries = []
    for source in sources:
        visited = set()
        find_reachables(source, node_edges, visited)
        for target in visited:
            if target != source and target in targets:
                queries.append((source, target))

    ppidimacs_str = ""
    pcnf_str = ""            
    
    ppidimacs_str += f'p cnf {len(edges)*2 + len(nodes)} {len(edges)+2}\n'

    for _ in edges:
        p_up = random.random()
        ppidimacs_str += f'c p distribution {p_up} {1 - p_up}\n'

    ppidimacs_nodes_id = {}
    current_id = len(edges)*2 + 1
    for node in nodes:
        ppidimacs_nodes_id[node['name']] = current_id
        current_id += 1
    for i, edge in enumerate(edges):
        s = ppidimacs_nodes_id[edge['start_node_name']]
        t = ppidimacs_nodes_id[edge['end_node_name']]
        ppidimacs_str += f'{t} -{s} -{2*i + 1} 0\n'
    
    #write pcnf input
    pcnf_str += f'p cnf {len(edges) + len(nodes)} {len(edges)}\n'
    pcnf_str += f'c p show {" ".join([str(x+1) for x in range(len(edges))])} 0\n'
    for v in range(len(edge)):
        pcnf_str += f'c p weight {v+1} {p_up} 0\nc p weight {-(v+1)} {1 - p_up} 0\n'
    pcnf_str += f''
    pcnf_nodes_id = {}
    current_id = len(edges)
    for node in nodes:
        pcnf_nodes_id[node['name']] = current_id
        current_id += 1
    for i, edge in enumerate(edges):
        s = pcnf_nodes_id[edge['start_node_name']]
        t = pcnf_nodes_id[edge['end_node_name']]
        pcnf_str += f'{t+1} -{s+1} -{i+1} 0\n'

    print(f"{len(queries)} queries")
    for query in queries:
        cache = {}
        find_used_edges(query[0], query[1], node_edges, 2*len(edges), cache, set())
        dist = [cache[edge['name']] if edge['name'] in cache else 2*len(edges) for edge in edges]
        number_used = len([x for x in dist if x != 2*len(edges)])
        number_skip = int(0.1*number_used)
        sorted_id = sorted([i for i in range(len(edges))], key=lambda x: cache[edges[x]['name']] if edges[x]['name'] in cache else len(edges)*2)
        learn_header = 'c p learn {}'.format(" ".join([str(x+1) for x in sorted_id[number_skip:]]))

        fout = open(os.path.join(ppidimacs_dir, name + f'_{query[0]}_{query[1]}.cnf'), 'w')
        fout.write(ppidimacs_str)
        fout.write(f'{ppidimacs_nodes_id[query[0]]}\n')
        fout.write(f'-{ppidimacs_nodes_id[query[1]]}\n')
        fout.write(learn_header)
        fout.close()
        
        fout = open(os.path.join(pcnf_dir, name + f'_{query[0]}_{query[1]}.cnf'), 'w')
        fout.write(pcnf_str)
        fout.write(f'{pcnf_nodes_id[query[0]]+1} 0\n')
        fout.write(f'-{pcnf_nodes_id[query[1]]+1} 0\n')
        fout.close()

files = ['Net1.json', 'Net2.json', 'Net3.json', 'Net6.json']
for filename in files:
    parse_file(filename)
