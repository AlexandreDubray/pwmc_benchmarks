import os
import itertools
from functools import reduce
import operator
import re

script_dir = os.path.dirname(os.path.realpath(__file__))
bif_dir = os.path.join(script_dir, 'bif')

def parse_variables(dataset):
    variables = {}
    with open(os.path.join(bif_dir, dataset + '.bif')) as f:
        lines = f.readlines()
        i = 0
        vid = 0
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
                        'id': vid
                        }
                vid += 1
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

def write_uai(instance):
    network_variables = parse_variables(instance)
    get_cpt(instance, network_variables)
    with open(os.path.join(script_dir, 'uai', f'{instance}.uai'), 'w') as f:
        # preamble
        # Type of network
        f.write('BAYES\n')
        # Number of variable
        f.write(f'{len(network_variables)}\n')
        # Domain of the variables
        f.write(' '.join([str(network_variables[v]["dom_size"]) for v in network_variables]) + '\n')
        # Number of function (CPT) in the newtork
        f.write(f'{len(network_variables)}\n')
        # For each CPT, the number of variable included in it, ending with the variable id
        for v in network_variables:
            parents = " ".join([str(network_variables[p]["id"]) for p in network_variables[v]['cpt']['parents_var']])
            if parents != "":
                f.write(f'{len(network_variables[v]["cpt"]["parents_var"]) + 1} {parents} {network_variables[v]["id"]}\n')
            else:
                f.write(f'{len(network_variables[v]["cpt"]["parents_var"]) + 1} {network_variables[v]["id"]}\n')

        f.write('\n')
        
        cpts = []
        for v in network_variables:
            number_values = sum([len(x) for x in network_variables[v]['cpt']['distributions']])
            lines = []
            for distribution in network_variables[v]['cpt']['distributions']:
                lines.append(' '.join([str(x) for x in distribution]))
            cpts.append("{}\n{}".format(
                number_values,
                " ".join(lines)
                ))
        f.write('\n'.join(cpts))




instances = [f.split('.')[0] for f in os.listdir(bif_dir) if os.path.isfile(os.path.join(bif_dir, f))]

for instance in instances:
    print(instance)
    write_uai(instance)
