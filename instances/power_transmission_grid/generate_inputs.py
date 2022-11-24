import os
import random

random.seed(52696698)

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
    with open(f'{dataset}/gridkit_{dataset.split("/")[1]}-highvoltage-vertices.csv') as f:
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
    with open(f'{dataset}/gridkit_{dataset.split("/")[1]}-highvoltage-links.csv') as f:
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

    with open(os.path.join(dataset, 'ppidimacs', f'{source}_{target}.ppidimacs'), 'w') as f:
        f.write(f'p cnf {len(nodes)+len(edges)*2} {len(clauses)}\n')
        f.write('\n'.join(distributions))
        f.write('\n')
        f.write('\n'.join(clauses))

def write_pcnf(dataset, nodes, edges, source, target):
    distributions_clauses = []
    for edge in edges:
        distributions_clauses += [f'{edge.var_id + 1} {edge.var_id + 2} 0',
                                  f'-{edge.var_id + 1} -{edge.var_id + 2} 0']
    clauses = [f'{nodes[source].var_id + 1} 0', f'-{nodes[target].var_id + 1} 0']
    for edge in edges:
        clauses.append(f'{nodes[edge.n1].var_id + 1} -{nodes[edge.n2].var_id +1} -{edge.var_id+1} 0')
        clauses.append(f'{nodes[edge.n2].var_id+1} -{nodes[edge.n1].var_id+1} -{edge.var_id+1} 0')

    with open(os.path.join(dataset, 'pcnf', f'{source}_{target}.cnf'), 'w') as f:
        f.write(f'p pcnf {len(nodes)+len(edges)*2} {len(clauses)+len(distributions_clauses)} {len(edges)*2}\n')
        f.write(f'vp {" ".join([str(x+1) for x in range(len(edges)*2)])} 0\n')
        f.write('\n'.join(distributions_clauses))
        f.write('\n')
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
        ]

for dataset in datasets:
    print(f'Processing {dataset}')
    os.makedirs(f'{dataset}/ppidimacs', exist_ok=True)
    os.makedirs(f'{dataset}/pcnf', exist_ok=True)
    nodes = get_nodes(dataset)
    edges = get_edges(dataset, nodes)
    for i in range(10):
        source = random.randint(0, len(nodes)-1)
        target = random.randint(0, len(nodes)-1)
        if source != target:
            write_ppidimacs(dataset, nodes, edges, source, target)
            write_pcnf(dataset, nodes, edges, source, target)

