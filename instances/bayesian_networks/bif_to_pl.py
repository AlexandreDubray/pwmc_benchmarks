import os
import itertools
from functools import reduce
import operator
import re

script_dir = os.path.dirname(os.path.realpath(__file__))
bif_dir = os.path.join(script_dir, 'bif')

def get_safe_lines(dataset):
    lines = open(dataset).readlines()
    for i in range(len(lines)):
        lines[i] = lines[i].replace('<', 'lt')
        lines[i] = lines[i].replace('>', 'gt')
        lines[i] = lines[i].replace('<=', 'lte')
        lines[i] = lines[i].replace('>=', 'gte')
        lines[i] = lines[i].replace('*', 'times')
        lines[i] = lines[i].replace('/', 'div')
        lines[i] = lines[i].lower()
    return lines

def remove_numbers(s):
    new_s = s
    for (old, new) in zip([str(x) for x in range(10)], ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']):
        new_s = new_s.replace(old, new)
    new_s = new_s.replace('<', 'lt')
    new_s = new_s.replace('>', 'gt')
    new_s = new_s.replace('<=', 'lte')
    new_s = new_s.replace('>=', 'gte')
    new_s = new_s.replace('+', 'plus')
    new_s = new_s.replace('-', 'minus')
    new_s = new_s.replace('*', 'times')
    new_s = new_s.replace('/', 'div')
    new_s = new_s.lower()
    return new_s

def parse_variables(dataset):
    variables = {}
    lines = get_safe_lines(os.path.join(bif_dir, dataset + '.bif'))
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('variable'):
            s = line.rstrip().split(' ')
            variable = s[1]
            domain_def = lines[i+1].rstrip().lstrip().split(' ')
            dom_size = int(domain_def[3])
            values = [remove_numbers(x.replace(',', '').replace('.', '').lower()) for x in domain_def[6:-1]]
            true_index = 0
            if len(values) == 2:
                if values[1] == 'true' or values[1] == 'yes':
                    true_index = 1
            variables[variable.lower()] = {
                    'is_leaf': True,
                    'domain': values,
                    'true_index': true_index,
                    }
            i += 2
        else:
            i += 1
    return variables

def get_variable_value_str(variables, var, value):
    pv = value.replace(',', '').replace('.', '').lower()
    if len(variables[var]['domain']) == 2:
        if pv == variables[var]['domain'][variables[var]['true_index']]:
            return var
        else:
            return f'\\+{var}'
    else:
        return f'{var}({pv})'

def pl_encoding(dataset):
    variables = parse_variables(dataset)
    clauses = []
    lines = get_safe_lines(os.path.join(bif_dir, dataset + '.bif'))
    cpt_variable_pattern = re.compile("probability \((.*)\) {")
    cpt_distribution_pattern = re.compile("\((.*)\) (.*)")
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('probability'):
            vars = cpt_variable_pattern.match(line).group(1).replace(',', '')
            s = vars.split('|')
            target_var = s[0].rstrip().lstrip().lower()
            parent_vars = [x.lower() for x in s[1].rstrip().lstrip().split(' ')] if len(s) > 1 else []
            for p in parent_vars:
                variables[p]['is_leaf'] = False
            i += 1
            line = lines[i].rstrip().lstrip().replace(',' , '').replace(';', '')
            distributions = []
            parents_domain = []
            if len(parent_vars) > 0:
                while line.rstrip() != "}":
                    pattern = cpt_distribution_pattern.match(line)
                    parents_value = [remove_numbers(x) for x in pattern.group(1).split(' ')]
                    probabilities = [float(x) for x in pattern.group(2).split(' ')]
                    parent_str = ', '.join([get_variable_value_str(variables, p, pv) for (p, pv) in zip(parent_vars, parents_value)])
                    if len(variables[target_var]["domain"]) > 2:
                        ad = []
                        for proba, value in zip(probabilities, variables[target_var]["domain"]):
                            var_str = get_variable_value_str(variables, target_var, value)
                            ad.append(f'{proba}::{var_str}')
                        clauses.append(f'{"; ".join(ad)} :- {parent_str}.')
                    else:
                        tidx = variables[target_var]['true_index']
                        clauses.append(f'{probabilities[tidx]}::{target_var} :- {parent_str}.')

                    i += 1
                    line = lines[i].rstrip().lstrip().replace(',', '').replace(';', '')
            else:
                probabilities = [float(x) for x in line.split(' ')[1:]]
                if len(variables[target_var]['domain']) == 2:
                    clauses.append(f'{probabilities[0]}::{target_var}.')
                else:
                    clauses.append('; '.join([f'{probabilities[i]}::{get_variable_value_str(variables, target_var, variables[target_var]["domain"][i])}' for i in range(len(probabilities))]) + '.')
        i += 1

    file_idx = 1
    for variable in variables:
        if variables[variable]['is_leaf']:
            if len(variables[variable]['domain']) > 2:
                for value in variables[variable]['domain']:
                    query = f'query({get_variable_value_str(variables, variable, value)}).'
                    with open(os.path.join(script_dir, 'pl', dataset, f'{file_idx}.pl'), 'w') as f:
                        f.write('\n'.join(clauses) + '\n')
                        f.write(query)
                        file_idx += 1
            else:
                query = f'query({variable}).'
                with open(os.path.join(script_dir, 'pl', dataset, f'{file_idx}.pl'), 'w') as f:
                    f.write('\n'.join(clauses) + '\n')
                    f.write(query)
                    file_idx += 1

instances = [f.split('.')[0] for f in os.listdir(bif_dir) if os.path.isfile(os.path.join(bif_dir, f))]

for instance in instances:
    print(instance)
    os.makedirs(os.path.join(script_dir, 'pl', instance), exist_ok=True)
    pl_encoding(instance)
