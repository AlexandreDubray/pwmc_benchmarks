import os
import itertools
from functools import reduce
import operator
import re
import random
import queue

script_dir = os.path.dirname(os.path.realpath(__file__))
bif_dir = os.path.join(script_dir, 'bif')

def parse_variables(dataset):
    variables = {}
    with open(os.path.join(bif_dir, dataset + '.bif')) as f:
        lines = f.readlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith('variable'):
                s = line.rstrip().split(' ')
                variable = s[1]
                domain_def = lines[i+1].rstrip().lstrip().split(' ')
                dom_size = int(domain_def[3])
                values = [x.replace(',', '') for x in domain_def[6:-1]]
                variables[variable] = {
                        'is_leaf': True,
                        'dom_size': dom_size,
                        'domain': values,
                        'distribution_index': [],
                        }
                i += 2
            else:
                i += 1
    return variables

def get_cpt(dataset, network_variables):
    with open(os.path.join(bif_dir, dataset + '.bif')) as f:
        lines = f.readlines()
        cpt_variable_pattern = re.compile("probability \((.*)\) {")
        cpt_distribution_pattern = re.compile("\((.*)\) (.*)")
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith('probability'):
                vars = cpt_variable_pattern.match(line).group(1).replace(',', '')
                s = vars.split('|')
                target_var = s[0].rstrip().lstrip()
                parent_vars = s[1].rstrip().lstrip().split(' ') if len(s) > 1 else []
                for p in parent_vars:
                    network_variables[p]['is_leaf'] = False
                i += 1
                line = lines[i].rstrip().lstrip().replace(',' , '').replace(';', '')
                distributions = []
                parents_domain = []
                if len(parent_vars) > 0:
                    while line.rstrip() != "}":
                        pattern = cpt_distribution_pattern.match(line)
                        parents_value = pattern.group(1).split(' ')
                        probabilities = [float(x) for x in pattern.group(2).split(' ')]
                        distributions.append(probabilities)
                        parents_domain.append(parents_value)
                        i += 1
                        line = lines[i].rstrip().lstrip().replace(',', '').replace(';', '')
                else:
                    probabilities = [float(x) for x in line.split(' ')[1:]]
                    distributions.append(probabilities)
                    parents_domain.append([])
                network_variables[target_var]['cpt'] = {
                        'distributions': distributions,
                        'parents_domain': parents_domain,
                        'parents_var': parent_vars,
                }
            i += 1
                
def get_dvar(network_variables, nvar, value):
    return network_variables[nvar]['deterministic_variables'][value]


def get_random_distributions(n):
    distribution = [random.random() for _ in range(n)]
    s = sum(distribution)
    return [x/s for x in distribution]

def pcnf_encoding(dataset):
    network_variables = parse_variables(dataset)
    get_cpt(dataset, network_variables)

    fixed_variable_per_query = {}
    for nvar in network_variables:
        if network_variables[nvar]['is_leaf']:
            distances = [(nvar, 0)]
            q = queue.Queue()
            for parent in network_variables[nvar]['cpt']['parents_var']:
                q.put((parent, 1))

            seen = set()
            while not q.empty():
                (pvar, dist) = q.get()
                if pvar not in seen:
                    distances.append((pvar, dist))
                    seen.add(pvar)
                    for parent in network_variables[pvar]['cpt']['parents_var']:
                        q.put((parent, dist + 1))
            distances = sorted(distances, key=lambda x: x[1])
            number_node_query = len(seen)
            number_node_known = int(0.1*number_node_query)
            fixed_variable_per_query[nvar] = [x[0] for x in distances[:number_node_known]]

    clauses = []
    distributions = []

    # First compute the variable index for each variable/distribution
    variable_index = 1
    for nvar in network_variables:
        cache = {}
        probabilistic_variables = []
        for distribution in network_variables[nvar]['cpt']['distributions']:
            if 1.0 in distribution:
                probabilistic_variables.append([])
                continue
            probabilistic_variables.append([])

            cache_key = tuple(x for x in sorted(distribution))
            
            if cache_key in cache:
                cached_entry = cache[cache_key]
                for _ in distribution:
                    probabilistic_variables[-1].append(None)
                idx = 0
                for _, index in sorted([(p, i) for i, p in enumerate(distribution)]):
                    probabilistic_variables[-1][index] = cached_entry[idx]
                    idx += 1
            else:
                cache_entry = []
                for p in distribution:
                    if p == 0.0:
                        probabilistic_variables[-1].append(None)
                        cache_entry.append((p, None))
                    else:
                        probabilistic_variables[-1].append(variable_index)
                        cache_entry.append((p, variable_index))
                        variable_index += 1
                distributions.append(f'c p distribution {" ".join([str(x) for x in distribution if x != 0.0])}')
                network_variables[nvar]['distribution_index'].append(len(distributions))
                cache[cache_key] = [x for _, x in sorted(cache_entry)]
        network_variables[nvar]['probabilistic_var'] = probabilistic_variables

    random_distributions = []
    for d in distributions:
        len_distri = len(d.split(' ')) - 3
        random_distributions.append(f'c p distribution {" ".join([str(x) for x in get_random_distributions(len_distri)])}')

    for nvar in network_variables:
        network_variables[nvar]['deterministic_variables'] = {}
        for nvar_value in network_variables[nvar]['domain']:
            network_variables[nvar]['deterministic_variables'][nvar_value] = variable_index
            variable_index += 1

    # Next we find the clause for each CPT entry
    for nvar in network_variables:
        n_distribution = len(network_variables[nvar]['cpt']['distributions'])
        for i in range(n_distribution):
            distribution = network_variables[nvar]['cpt']['distributions'][i]
            par_domain = network_variables[nvar]['cpt']['parents_domain'][i]

            parent_var = [f'-{get_dvar(network_variables, network_variables[nvar]["cpt"]["parents_var"][k], par_domain[k])}' for k in range(len(par_domain))]

            if 1.0 in distribution:
                for j in range(len(distribution)):
                    if distribution[j] == 1.0:
                        target_value = network_variables[nvar]['deterministic_variables'][network_variables[nvar]['domain'][j]]
                        clauses.append('{} {} 0'.format(
                            ' '.join(parent_var),
                            f'{target_value}',
                            ))
                        break
            else:
                for j in range(len(distribution)):
                    if distribution[j] != 0.0:
                        prob_var = network_variables[nvar]['probabilistic_var'][i][j]
                        target_value = network_variables[nvar]['deterministic_variables'][network_variables[nvar]['domain'][j]]
                        clauses.append('{} {} {} 0'.format(
                            ' '.join(parent_var),
                            f'-{prob_var}',
                            f'{target_value}',
                            ))

    file_idx = 1
    os.makedirs(os.path.join(script_dir, 'pcnf', dataset), exist_ok=True)
    os.makedirs(os.path.join(script_dir, 'pcnf_learn', dataset), exist_ok=True)
    os.makedirs(os.path.join(script_dir, 'pcnf_partial', dataset), exist_ok=True)
    for nvar in network_variables:
        if network_variables[nvar]['is_leaf']:
            dsk = set()
            partial_distributions = []
            for fixed in fixed_variable_per_query[nvar]:
                for dixd in network_variables[fixed]['distribution_index']:
                    dsk.add(dixd)

            learn_distribution = [i for i in range(1, len(distributions)+1) if i not in dsk]

            for i in range(len(distributions)):
                if i not in dsk:
                    partial_distributions.append(random_distributions[i])
                else:
                    partial_distributions.append(distributions[i])
            header_learn = 'c p learn {}'.format(' '.join([str(x) for x in learn_distribution]))

            for i in range(network_variables[nvar]['dom_size']):
                with open(os.path.join(script_dir, 'pcnf', dataset, f'{file_idx}.cnf'), 'w') as f:
                    f.write(f'p cnf {variable_index} {len(clauses) + network_variables[nvar]["dom_size"] - 1}\n')
                    f.write(f'c Querying variable {nvar} with value {network_variables[nvar]["domain"][i]}\n')
                    f.write('\n'.join(distributions) + '\n')
                    f.write('\n'.join(clauses) + '\n')
                    for j in range(network_variables[nvar]['dom_size']):
                        if i != j:
                            f.write(f'-{network_variables[nvar]["deterministic_variables"][network_variables[nvar]["domain"][j]]} 0\n')

                with open(os.path.join(script_dir, 'pcnf_partial', dataset, f'{file_idx}.cnf'), 'w') as f:
                    f.write(f'p cnf {variable_index} {len(clauses) + network_variables[nvar]["dom_size"] - 1}\n')
                    f.write(f'c Querying variable {nvar} with value {network_variables[nvar]["domain"][i]}\n')
                    if len(learn_distribution) > 0:
                        f.write(header_learn + '\n')
                    f.write('\n'.join(partial_distributions) + '\n')
                    f.write('\n'.join(clauses) + '\n')
                    for j in range(network_variables[nvar]['dom_size']):
                        if i != j:
                            f.write(f'-{network_variables[nvar]["deterministic_variables"][network_variables[nvar]["domain"][j]]} 0\n')

                with open(os.path.join(script_dir, 'pcnf_learn', dataset, f'{file_idx}.cnf'), 'w') as f:
                    f.write(f'p cnf {variable_index} {len(clauses) + network_variables[nvar]["dom_size"] - 1}\n')
                    f.write(f'c Querying variable {nvar} with value {network_variables[nvar]["domain"][i]}\n')
                    f.write('\n'.join(random_distributions) + '\n')
                    f.write('\n'.join(clauses) + '\n')
                    for j in range(network_variables[nvar]['dom_size']):
                        if i != j:
                            f.write(f'-{network_variables[nvar]["deterministic_variables"][network_variables[nvar]["domain"][j]]} 0\n')
                
                file_idx += 1

instances = [f.split('.')[0] for f in os.listdir(bif_dir) if os.path.isfile(os.path.join(bif_dir, f))]

for instance in instances:
    print(instance)
    pcnf_encoding(instance)
