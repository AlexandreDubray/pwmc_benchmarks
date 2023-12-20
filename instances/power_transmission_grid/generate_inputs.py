import os
import random
import re
import queue

random.seed(52696698)

_script_dir = os.path.dirname(os.path.realpath(__file__))

def safe_str_bash(s):
    return re.sub('[\s $\#=!<>|;{}~&]', '_', s)

class Node:

    def __init__(self, node_id):
        self.node_id = node_id
        self.edges = []

    def add_edge(self, edge):
        self.edges.append(edge)

    def set_var_id(self, var_id):
        self.var_id = var_id
        
    def is_extremity(self):
        return len(self.edges) == 1

class Edge:

    def __init__(self, edge_id, n1, n2, var_id):
        self.edge_id = edge_id
        self.n1 = n1
        self.n2 = n2
        self.proba_down = random.random()
        self.var_id = var_id
        
    def __str__(self):
        f"[{self.n1}-{self.n2}]"


def get_nodes(dataset):
    nodes = []
    with open(os.path.join(_script_dir, f'{dataset}/gridkit_{dataset.split("/")[1]}-highvoltage-vertices.csv')) as f:
        first = True
        for line in f:
            if first:
                first = False
                continue
            s = line.split(',')
            node_id = int(s[0])
            nodes.append(Node(node_id))
    return nodes

def get_edges(dataset, nodes):
    edges = []
    map_node_id = {node.node_id: i for i, node in enumerate(nodes)}
    with open(os.path.join(_script_dir, f'{dataset}/gridkit_{dataset.split("/")[1]}-highvoltage-links.csv')) as f:
        first = True
        var_id = 1
        for line in f:
            if first:
                first = False
                continue
            s = line.split(',')
            edge_id = int(s[0])
            n1 = map_node_id[int(s[1])]
            n2 = map_node_id[int(s[2])]
            edge = Edge(edge_id, n1, n2, var_id)
            edges.append(edge)
            nodes[n1].add_edge(edge)
            nodes[n2].add_edge(edge)
            # two variables (up down) per edge
            var_id += 2
        for node in nodes:
            node.set_var_id(var_id)
            var_id += 1
    return edges

def find_dist(nodes, edges, source, target):
    distance = {}
    q = queue.Queue()
    q.put((source, 0))
    seen_nodes = {source}
    while not q.empty():
        (node, dist) = q.get()
        seen_nodes.add(node)
        for edge in nodes[node].edges:
            if edge not in distance:
                distance[edge] = dist
            for neighbor in [edge.n1, edge.n2]:
                if neighbor not in seen_nodes:
                    q.put((neighbor, dist + 1))
    for edge in edges:
        if edge not in distance:
            distance[edge] = 2*len(edges)
    return distance

def write_ppidimacs(dataset, nodes, edges, source, target):
    distances = find_dist(nodes, edges, source, target)
    edges_sorted = sorted([(i, x) for (i, x) in enumerate(edges)], key=lambda x: distances[x[1]])
    number_edge_useful = len([x for x in distances if distances[x] != len(edges)*2])
    start_idx = int(0.1*number_edge_useful)
    edge_learn = []
    for i in range(len(edges)-1, start_idx, -1):
        (idx, e) = edges_sorted[i]
        edge_learn.append(idx + 1)

    distributions = [f'c p distribution {1.0 - edge.proba_down} {edge.proba_down}' for edge in edges]
    learn_header = 'c p learn {}'.format(' '.join([str(x) for x in edge_learn]))
    clauses = [f'{nodes[source].var_id} 0', f'{-nodes[target].var_id} 0']
    for edge in edges:
        clauses.append(f'{nodes[edge.n1].var_id} -{nodes[edge.n2].var_id} -{edge.var_id} 0')
        clauses.append(f'{nodes[edge.n2].var_id} -{nodes[edge.n1].var_id} -{edge.var_id} 0')

    with open(os.path.join(_script_dir, 'schlandals', dataset, f'{source}_{target}.cnf'), 'w') as f:
        f.write(f'p cnf {len(nodes)+len(edges)*2} {len(clauses)}\n')
        f.write('\n'.join(distributions) + '\n')
        f.write(learn_header + '\n')
        f.write('\n'.join(clauses))

def write_pcnf(dataset, nodes, edges, source, target):
    clauses = [f'{nodes[source].var_id + 1 -len(edges)} 0', f'-{nodes[target].var_id + 1 - len(edges)} 0']
    for edge in edges:
        clauses.append(f'{nodes[edge.n1].var_id + 1 - len(edges)} -{nodes[edge.n2].var_id +1 - len(edges)} -{int((edge.var_id/2)+1)} 0')
        clauses.append(f'{nodes[edge.n2].var_id+1-len(edges)} -{nodes[edge.n1].var_id+1-len(edges)} -{int((edge.var_id/2)+2)} 0')

    with open(os.path.join(_script_dir, 'pcnf', dataset, f'{source}_{target}.cnf'), 'w') as f:
        f.write(f'p cnf {len(nodes)+len(edges)} {len(clauses)}\n')
        f.write(f'c p show {" ".join([str(x+1) for x in range(len(edges))])} 0\n')
        for x in range(len(edges)):
            f.write(f'c p weight {x+1} {1.0 - edges[x].proba_down} 0\nc p weight {-(x+1)} {edges[x].proba_down} 0\n')
        f.write('\n'.join(clauses))

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
        
def has_path(source, target, nodes, edges, visited, path):
    if source == target:
        return True
    visited[source] = True
    for edge in nodes[source].edges:
        from_node = edge.n1
        to_node = edge.n2
        if from_node == source and not visited[to_node] and has_path(to_node, target, nodes, edges, visited, path):
            path.append(source)
            return True
    return False

for dataset in datasets:
    print(f'Processing {dataset}')
    s = dataset.split('/')
    continent = s[0]
    sub_region = safe_str_bash(s[1])
    os.makedirs(os.path.join(_script_dir, 'schlandals', f'{continent}/{sub_region}'), exist_ok=True)
    os.makedirs(os.path.join(_script_dir, 'pcnf', f'{continent}/{sub_region}'), exist_ok=True)
    nodes = get_nodes(f'{continent}/{sub_region}')
    edges = get_edges(f'{continent}/{sub_region}', nodes)
    in_a_query = [False for _ in nodes]
    targets = [i for i in range(len(nodes))]
    for source in range(len(nodes)):
        if in_a_query[source]:
            continue
        random.shuffle(targets)
        for target in targets:
            path = []
            if source != target and has_path(source, target, nodes, edges, [False for _ in nodes], path):
                in_a_query[source] = True
                in_a_query[target] = True
                for n in path:
                    in_a_query[n] = True
                write_ppidimacs(f'{continent}/{sub_region}', nodes, edges, source, target)
                write_pcnf(f'{continent}/{sub_region}', nodes, edges, source, target)
                break
