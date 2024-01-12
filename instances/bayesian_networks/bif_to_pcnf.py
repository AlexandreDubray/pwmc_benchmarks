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

    clauses = []
    distributions = []

    enc_1_distribution_pointer = {}
    # First compute the variable index for each variable/distribution
    variable_index = 1
    for nvar in network_variables:
        enc_1_distribution_pointer[nvar] = []
        cache = {}
        enc_1_ptr_cache = {}
        probabilistic_variables = []
        for distribution in network_variables[nvar]['cpt']['distributions']:
            if 1.0 in distribution:
                enc_1_distribution_pointer[nvar].append(None)
                probabilistic_variables.append([])
                continue
            probabilistic_variables.append([])

            cache_key = tuple(x for x in sorted(distribution))
            
            if cache_key in cache:
                enc_1_distribution_pointer[nvar].append(enc_1_ptr_cache[cache_key])
                cached_entry = cache[cache_key]
                for _ in distribution:
                    probabilistic_variables[-1].append(None)
                idx = 0
                for _, index in sorted([(p, i) for i, p in enumerate(distribution)]):
                    probabilistic_variables[-1][index] = cached_entry[idx]
                    idx += 1
            else:
                enc_1_distribution_pointer[nvar].append(len(distributions))
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
                enc_1_ptr_cache[cache_key] = len(distributions) - 1
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

    variable_rank = {}
    q = queue.Queue()
    nleaves = 0
    for v in network_variables:
        if network_variables[v]['is_leaf']:
            nleaves += 1
            q.put((v, 0))

    while not q.empty():
        (v, dist) = q.get()
        if v not in variable_rank:
            variable_rank[v] = dist
            for parent in network_variables[v]['cpt']['parents_var']:
                q.put((parent, dist+1))

    ratio_fix = 0.7
    v_not_learned = int(ratio_fix * len(network_variables))
    print(len(network_variables), nleaves, v_not_learned)
    x = sorted([v for v in network_variables], key=lambda x: variable_rank[x])[:v_not_learned]
    dsk = set()
    for v in x:
        for didx in network_variables[v]['distribution_index']:
            if random.random() < 1.0:
                dsk.add(didx)
    print(len(distributions), len(dsk), len(dsk)/len(distributions))
    partial_distributions = []
    for i in range(len(distributions)):
        if i+1 not in dsk:
            partial_distributions.append(random_distributions[i])
        else:
            partial_distributions.append(distributions[i])
    header_learn = 'c p learn {}'.format(' '.join([str(x+1) for x in range(len(distributions)) if x+1 not in dsk]))

    file_idx = 1
    os.makedirs(os.path.join(script_dir, 'pcnf', dataset), exist_ok=True)
    os.makedirs(os.path.join(script_dir, 'pcnf_learn', dataset), exist_ok=True)
    os.makedirs(os.path.join(script_dir, 'pcnf_partial', dataset), exist_ok=True)
    for nvar in network_variables:
        if network_variables[nvar]['is_leaf']:
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
                    if len(dsk) > 0:
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


    enc1_clauses = []
    enc1_weights = []
    enc1_random_weights = []

    variable_index = 1
    indicator_variables = {}
    for variable in network_variables:
        indicator_variables[variable] = {}
        indicators = []
        for i in range(network_variables[variable]['dom_size']):
            indicators.append(variable_index)
            indicator_variables[variable][network_variables[variable]['domain'][i]] = variable_index
            enc1_weights.append(f'1.0')
            enc1_weights.append(f'1.0')
            enc1_random_weights.append(f'1.0')
            enc1_random_weights.append(f'1.0')
            variable_index += 1
        
        enc1_clauses.append(' '.join([f'{x}' for x in indicators]) + ' 0')

        for i in range(len(indicators)):
            for j in range(i+1, len(indicators)):
                enc1_clauses.append(f'-{indicators[i]} -{indicators[j]} 0')

    os.makedirs(os.path.join(script_dir, 'enc1', dataset), exist_ok= True)
    os.makedirs(os.path.join(script_dir, 'enc1_learn', dataset), exist_ok= True)

    fdist_file = open(os.path.join(script_dir, 'enc1', f'{dataset}.dist'), 'w')
    for variable in network_variables:
        parent_variables = network_variables[variable]['cpt']['parents_var']
        n_distributions = len(network_variables[variable]['cpt']['distributions'])
        for i in range(n_distributions):
            distribution = network_variables[variable]['cpt']['distributions'][i]
            if enc_1_distribution_pointer[variable][i] is None:
                sch_random_distribution = [x for x in distribution]
            else:
                sch_random_distribution = [float(x) for x in random_distributions[enc_1_distribution_pointer[variable][i]].split(' ')[3:]]
            parent_domain = network_variables[variable]['cpt']['parents_domain'][i]

            pvs = [indicator_variables[parent_variables[j]][parent_domain[j]] for j in range(len(parent_domain))]

            probabilistic_vars = [0 for _ in distribution]
            sch_ptr_idx = 0
            for sub_i, p in enumerate(distribution):
                if p != 0.0:
                    probabilistic_vars[sub_i] = variable_index
                    enc1_weights.append(f'{p}')
                    enc1_weights.append(f'1.0')
                    enc1_random_weights.append(f'{sch_random_distribution[sch_ptr_idx]}')
                    enc1_random_weights.append(f'1.0')
                    variable_index += 1
                    sch_ptr_idx += 1
                else:
                    if enc_1_distribution_pointer[variable][i] is None:
                        sch_ptr_idx += 1
                    probabilistic_vars[sub_i] = None

            fdist_file.write(' '.join([str(x) for x in probabilistic_vars if x is not None]) + '\n')
            fdist_file.write(' '.join([str(x) for i, x in enumerate(distribution) if probabilistic_vars[i] is not None]) + '\n')

            for j, p in enumerate(distribution):
                if p != 0.0:
                    target_var = indicator_variables[variable][network_variables[variable]['domain'][j]]
                    proba_var = probabilistic_vars[j]

                    implicant = [x for x in pvs] + [target_var]
                    enc1_clauses.append('{} {} 0'.format(
                        " ".join([str(-x) for x in implicant]),
                        proba_var
                        ))

                    for x in implicant:
                        enc1_clauses.append(f'-{proba_var} {x} 0')
                else:
                    target_var = indicator_variables[variable][network_variables[variable]['domain'][j]]
                    implicant = [x for x in pvs] + [target_var]
                    enc1_clauses.append('{} 0'.format(
                        " ".join([str(-x) for x in implicant]),
                        ))


    file_idx = 1
    for nvar in network_variables:
            if network_variables[nvar]['is_leaf']:
                for i in range(network_variables[nvar]['dom_size']):
                    with open(os.path.join(script_dir, 'enc1', dataset, f'{file_idx}.cnf'), 'w') as f:
                        f.write(f'p cnf {variable_index - 1} {len(enc1_clauses) + 1}\n')
                        f.write(f'c Querying variable {nvar} with value {network_variables[nvar]["domain"][i]}\n')
                        f.write('c weights ' + ' '.join(enc1_weights) + '\n')
                        f.write('\n'.join(enc1_clauses) + '\n')
                        f.write(f'{indicator_variables[nvar][network_variables[nvar]["domain"][i]]} 0\n')

                    with open(os.path.join(script_dir, 'enc1_learn', dataset, f'{file_idx}.cnf'), 'w') as f:
                        f.write(f'p cnf {variable_index - 1} {len(enc1_clauses) + 1}\n')
                        f.write(f'c Querying variable {nvar} with value {network_variables[nvar]["domain"][i]}\n')
                        f.write('c weights ' + ' '.join(enc1_random_weights) + '\n')
                        f.write('\n'.join(enc1_clauses) + '\n')
                        f.write(f'{indicator_variables[nvar][network_variables[nvar]["domain"][i]]} 0\n')
                    file_idx += 1
    

instances = [f.split('.')[0] for f in os.listdir(bif_dir) if os.path.isfile(os.path.join(bif_dir, f))]

for instance in instances:
    print(instance)
    pcnf_encoding(instance)
