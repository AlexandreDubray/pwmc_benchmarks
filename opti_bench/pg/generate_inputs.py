import os
import random
import re
import queue

random.seed(52696698)

_script_dir = os.path.dirname(os.path.realpath(__file__))

def safe_str_bash(s):
    return re.sub('[\s $\#=!<>|;{}~&]', '_', s)

def parse_dataset(dataset):
    nodes = []
    with open(os.path.join(_script_dir, f'{dataset}/gridkit_{dataset.split("/")[1]}-highvoltage-vertices.csv')) as f:
        first = True
        for line in f:
            if first:
                first = False
                continue
            s = line.split(',')
            node_id = int(s[0])
            nodes.append(node_id)

    edges = {node: [] for node in nodes}
    with open(os.path.join(_script_dir, f'{dataset}/gridkit_{dataset.split("/")[1]}-highvoltage-links.csv')) as f:
        first = True
        for line in f:
            if first:
                first = False
                continue
            s = line.split(',')
            edge_id = int(s[0])
            n1 = int(s[1])
            n2 = int(s[2])
            proba_up = random.random()
            proba_learning = random.random()
            edges[n1].append((n2, proba_up, proba_learning))
            edges[n2].append((n1, proba_up, proba_learning))
    return (nodes, edges)

def sch_encoding(nodes, edges, queries, dataset):
    distributions = []
    clauses = []
    current_id = 1
    map_edge_id = {}
    for node in edges:
        for (to, proba) in edges[node]:
            if node < to:
                if (to, node) not in map_edge_id:
                    distributions.append(f'c p distribution {proba} {1.0 - proba}')
                    map_edge_id[(node, to)] = current_id
                    map_edge_id[(to, node)] = current_id
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

    for (source, target) in queries:

        with open(os.path.join(_script_dir, 'sch', dataset, f'{source}_{target}.cnf'), 'w') as f:
            f.write(f'p cnf {current_id} {len(clauses) + 2}\n')
            f.write('\n'.join(distributions) + '\n')
            f.write('\n'.join(clauses) + '\n')
            f.write(f'{map_node_id[source]} 0\n')
            f.write(f'-{map_node_id[target]} 0')

def pcnf_encoding(nodes, edges, queries, dataset):
    clauses = []
    weights = []
    current_id = 1
    map_edge_id = {}
    for node in edges:
        for (to, proba, _) in edges[node]:
            if (to, node) not in map_edge_id:
                weights.append(f'c p weight {current_id} {proba} 0')
                weights.append(f'c p weight -{current_id} {1.0 - proba} 0')
                map_edge_id[(node, to)] = current_id
                current_id += 1
            else:
                map_edge_id[(node, to)] = map_edge_id[(to, node)]

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

    for (source, target) in queries:
        with open(os.path.join(_script_dir, 'pcnf', dataset, f'{source}_{target}.cnf'), 'w') as f:
            f.write(f'p cnf {current_id} {len(clauses) + 2}\n')
            f.write(projected_header + '\n')
            f.write('\n'.join(weights) + '\n')
            f.write('\n'.join(clauses) + '\n')
            f.write(f'{map_node_id[source]} 0\n')
            f.write(f'-{map_node_id[target]} 0')

def pl_encoding(nodes, edges, queries, dataset):
    seen_edges = set()
    clauses = []
    clauses_learn = []
    for node in edges:
        for (to, proba) in edges[node]:
            if node < to:
                edge = (node, to)
                if edge not in seen_edges:
                    clauses.append(f'{proba}::edge({node},{to}).')
                    seen_edges.add(edge)

    for (source, target) in queries:

        with open(os.path.join(_script_dir, 'pl', dataset, f'{source}_{target}.pl'), 'w') as f:
            f.write('\n'.join(clauses) + '\n')
            f.write('edge(X, Y) :- edge(Y, X).\n')
            f.write('path(X, Y) :- edge(X, Y).\n')
            f.write('path(X, Y) :- edge(X, Z), path(Z, Y).\n')
            f.write(f'query(path({source},{target})).')

datasets = [
        'europe/Albania',
        'europe/Armenia',
        'europe/Austria',
        'europe/Belarus',
        'europe/Belgium',
        'europe/Bosnia and Herzegovina',
        'europe/Bulgaria',
        'europe/Croatia',
        'europe/Czech Republic',
        'europe/Denmark',
        'europe/Estonia',
        'europe/Finland',
        'europe/France',
        'europe/Georgia',
        'europe/Germany',
        'europe/Greece',
        'europe/Hungary',
        'europe/Iceland',
        'europe/Ireland',
        'europe/Italy',
        'europe/Latvia',
        'europe/Lithuania',
        'europe/Luxembourg',
        'europe/Montenegro',
        'europe/Netherlands',
        'europe/Norway',
        'europe/Poland',
        'europe/Portugal',
        'europe/Republic of Moldova',
        'europe/Romania',
        'europe/Russia',
        'europe/Serbia',
        'europe/Slovakia',
        'europe/Slovenia',
        'europe/Spain',
        'europe/Sweden',
        'europe/Switzerland',
        'europe/The former Yugoslav Republic of Macedonia',
        'europe/Turkey',
        'europe/Ukraine',
        'europe/United Kingdom',
        'north_america/Alabama',
        'north_america/Alaska',
        'north_america/Arizona',
        'north_america/Arkansas',
        'north_america/California',
        'north_america/Connecticut',
        'north_america/Delaware',
        'north_america/Florida',
        'north_america/Georgia',
        'north_america/Idaho',
        'north_america/Illinois',
        'north_america/Iowa',
        'north_america/Kansas',
        'north_america/Kentucky',
        'north_america/Louisiana',
        'north_america/Maine',
        'north_america/Maryland',
        'north_america/Massachusetts',
        'north_america/Michigan',
        'north_america/Minnesota',
        'north_america/Mississippi',
        'north_america/Missouri',
        'north_america/Montana',
        'north_america/Nebraska',
        'north_america/Nevada',
        'north_america/New Hampshire',
        'north_america/New Jersey',
        'north_america/New Mexico',
        'north_america/New York',
        'north_america/North Carolina',
        'north_america/North Dakota',
        'north_america/Ohio',
        'north_america/Oklahoma',
        'north_america/Oregon',
        'north_america/Pennsylvania',
        'north_america/Rhode Island',
        'north_america/South Carolina',
        'north_america/South Dakota',
        'north_america/Tennessee',
        'north_america/Texas',
        'north_america/Utah',
        'north_america/Vermont',
        'north_america/Virginia',
        'north_america/Washington',
        'north_america/West Virginia',
        'north_america/Wisconsin',
        'north_america/Wyoming',
]

def find_path(source, target, nodes, edges, visited, path):
    if source == target:
        path.add(target)
        return True
    visited.add(source)
    for (node, _, _) in edges[source]:
        if node not in visited:
            if find_path(node, target, nodes, edges, visited, path):
                path.add(source)
                return True
    return False

for dataset in datasets:
    print(f'Processing {dataset}')
    s = dataset.split('/')
    continent = s[0]
    sub_region = safe_str_bash(s[1])
    dataset_input = f'{continent}/{sub_region}'
    os.makedirs(os.path.join(_script_dir, 'sch', dataset_input), exist_ok=True)
    os.makedirs(os.path.join(_script_dir, 'pcnf', dataset_input), exist_ok=True)
    os.makedirs(os.path.join(_script_dir, 'pl', dataset_input), exist_ok=True)
    (nodes, edges) = parse_dataset(dataset_input)
    nodes = [x for x in nodes if len(edges[x]) > 0]
    to_query = [x for x in nodes]
    queries = set()
    while len(to_query) > 0:
        source = random.sample(to_query, 1)[0]
        target = random.sample([x for x in nodes if x != source], 1)[0]
        path = set()
        if find_path(source, target, nodes, edges, set(), path):
            queries.add((source, target))
            to_query = [x for x in to_query if x not in path]

    print(f'\t{len(queries)} queries')
    sch_encoding(nodes, edges, queries, dataset_input)
    pcnf_encoding(nodes, edges, queries, dataset_input)
    pl_encoding(nodes, edges, queries, dataset_input)
