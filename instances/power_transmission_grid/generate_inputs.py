import os
import random
import re

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

class Edge:

    def __init__(self, edge_id, n1, n2, var_id):
        self.edge_id = edge_id
        self.n1 = n1
        self.n2 = n2
        self.proba_down = 0.125
        self.var_id = var_id

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
        var_id = 0
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

def write_ppidimacs(dataset, nodes, edges, source, target):
    distributions = [f'd {1.0 - edge.proba_down} {edge.proba_down}' for edge in edges]
    clauses = [f'{nodes[source].var_id}', f'{-nodes[target].var_id}']
    for edge in edges:
        clauses.append(f'{nodes[edge.n1].var_id} -{nodes[edge.n2].var_id} -{edge.var_id}')
        clauses.append(f'{nodes[edge.n2].var_id} -{nodes[edge.n1].var_id} -{edge.var_id}')

    with open(os.path.join(_script_dir, dataset, 'ppidimacs', f'{source}_{target}.ppidimacs'), 'w') as f:
        f.write(f'p cnf {len(nodes)+len(edges)*2} {len(clauses)}\n')
        f.write('\n'.join(distributions))
        f.write('\n')
        f.write('\n'.join(clauses))

def write_pcnf(dataset, nodes, edges, source, target):
    clauses = [f'{nodes[source].var_id + 1 -len(edges)} 0', f'-{nodes[target].var_id + 1 - len(edges)} 0']
    for edge in edges:
        clauses.append(f'{nodes[edge.n1].var_id + 1 - len(edges)} -{nodes[edge.n2].var_id +1 - len(edges)} -{int((edge.var_id/2)+1)} 0')
        clauses.append(f'{nodes[edge.n2].var_id+1-len(edges)} -{nodes[edge.n1].var_id+1-len(edges)} -{int((edge.var_id/2)+1)} 0')

    with open(os.path.join(_script_dir, dataset, 'pcnf', f'{source}_{target}.cnf'), 'w') as f:
        f.write(f'p pcnf {len(nodes)+len(edges)} {len(clauses)} {len(edges)}\n')
        #f.write(f'vp {" ".join([str(x+1) for x in range(len(edges))])} 0\n')
        f.write(f'c p show {" ".join([str(x+1) for x in range(len(edges))])} 0\n')
        for x in range(len(edges)):
            f.write(f'c p weight {x+1} {0.875} 0\nc p weight {-(x+1)} 0.125 0\n')
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

for dataset in datasets:
    print(f'Processing {dataset}')
    s = dataset.split('/')
    continent = s[0]
    sub_region = safe_str_bash(s[1])
    os.makedirs(os.path.join(_script_dir, f'{continent}/{sub_region}/ppidimacs'), exist_ok=True)
    os.makedirs(os.path.join(_script_dir, f'{continent}/{sub_region}/pcnf'), exist_ok=True)
    nodes = get_nodes(f'{continent}/{sub_region}')
    edges = get_edges(f'{continent}/{sub_region}', nodes)
    for i in range(10):
        source = random.randint(0, len(nodes)-1)
        target = random.randint(0, len(nodes)-1)
        if source != target:
            write_ppidimacs(f'{continent}/{sub_region}', nodes, edges, source, target)
            write_pcnf(f'{continent}/{sub_region}', nodes, edges, source, target)

