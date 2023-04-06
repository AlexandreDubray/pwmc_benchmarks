import random
import re
import os
import numpy as np

_script_dir = os.path.dirname(os.path.realpath(__file__))
random.seed(862453179)

def safe_str_bash(s):
    return re.sub('[\s $\#=!<>|;{}~&]', '_', s)


class CPT:

    def __init__(self, head, body):
        self.head = head
        self.body = body
        self.entries = []
        self.parent_domains = []
        self.ppidimacs_var = []

class Variable:
    
    def __init__(self, name, values, values_offset):
        self.name = name
        self.values = {}
        self.value_names = values
        for i in range(len(values)):
            self.values[values[i]] = i + values_offset
        self.parents = []
        self.cpt = None
        self.is_leaf = True

    def get_var_from_id(self, i):
        return self.values[self.value_names[i]]
        

def parse_network(input_file):
    with open(input_file) as f:
        lines = f.readlines()

    variables = []
    variables_map = {}
    for i in range(len(lines)):
        lines[i] = lines[i].lstrip().rstrip().replace('/', '-')

    # Parsing all the variable definitions
    i = 0
    values_offset = 0
    while not lines[i].startswith("probability"):
        if lines[i].startswith("variable"):
            variable_name = lines[i].rstrip().split(' ')[1]
            i += 1
            variable_def = lines[i].rstrip().split(' ')
            # for now only discrete BN are supported
            assert(variable_def[1] == 'discrete')
            variable_values = [x for x in variable_def[6:-1]]
            for j in range(len(variable_values)):
                variable_values[j] = re.sub('\(|\)|,', '', variable_values[j])
            variable = Variable(variable_name, variable_values, values_offset)
            values_offset += len(variable_values)
            variables.append(variable)
            variables_map[variable_name] = variable
        i += 1

    
    while i < len(lines):
        split = lines[i].split(' ')
        target_variable_name = split[2]
        variable = variables_map[target_variable_name]

        variable.parents = [variables_map[x.rstrip().lstrip().replace(',', '')] for x in split[4:-2]]

        assert(variable.name == split[2])
        for p in variable.parents:
            p.is_leaf = False

        cpt = CPT(variable, variable.parents)
        i += 1
        
        nb_lines = 1
        for p in variable.parents:
            nb_lines *= len(p.values)
        parents = variable.parents
        for lid in range(nb_lines):
            cpt_line = lines[i].split(' ')
            parent_values = [parents[j].values[re.sub('\(|\)|,', '', cpt_line[j])] for j in range(len(parents))]
            probabilities = re.findall("\d\.\d+(?:e-\d\d)?", lines[i])
            cpt.entries.append(probabilities)
            cpt.parent_domains.append(parent_values)
            i += 1
        variable.cpt = cpt
        i += 1
    return variables

def write_network(outdir, variables, prop_evidence):
    os.makedirs(os.path.join(_script_dir, 'ppidimacs',outdir), exist_ok=True)
    os.makedirs(os.path.join(_script_dir, 'pcnf', outdir), exist_ok=True)
    in_evidence = [not v.is_leaf and random.random() <= prop_evidence for v in variables]
    selected_values = [random.randint(0, len(v.values) - 1) for v in variables]

    clauses = []
    distribution_lines = []
    clauses_cnf = []
    cnf_weights = []

    # First we compute the distributions, this also give the var id for the probabilistic variables
    cpt_var_id = 0
    for var in variables:
        for distribution in var.cpt.entries:
            distribution_lines.append('d ' + ' '.join(['{}'.format(x) for x in distribution]))
            var.cpt.ppidimacs_var.append([cpt_var_id + i for i in range(len(var.values))])
            for i, w in enumerate(distribution):
                cnf_weights.append(f'c p weight {cpt_var_id + i + 1} {w} 0')
            cpt_var_id = var.cpt.ppidimacs_var[-1][-1] + 1

    for vid, var in enumerate(variables):
        for didx in range(len(var.cpt.entries)):
            parent_var_ids = var.cpt.parent_domains[didx]

            # for the CNF files, we have to input the distributions in the clauses
            # We need to select at least 1 of the variables: v1 OR v2 or ... or vN
            clauses_cnf.append(" ".join([str(x+1) for x in var.cpt.ppidimacs_var[didx]]) + " 0")
            for i in range(len(var.cpt.ppidimacs_var[didx])):
                for j in range(i+1, len(var.cpt.ppidimacs_var[didx])):
                    # But each is mutually exclusive -> !(v1 and v2) <=> !v1 or !v2
                    v1 = var.cpt.ppidimacs_var[didx][i]
                    v2 = var.cpt.ppidimacs_var[didx][j]
                    clauses_cnf.append(f'-{v1+1} -{v2+1} 0')

            # The actual clauses: Px and pa1 and pa2 and ... and paM =>Vx
            for vidx in range(len(var.values)):
                head = var.get_var_from_id(vidx) + cpt_var_id
                body = [cpt_var_id + x for x in parent_var_ids] + [var.cpt.ppidimacs_var[didx][vidx]]
                clauses.append(f'{head} ' + ' '.join([f'-{x}' for x in body]))
                
                clauses_cnf.append(f'{head+1} ' + ' '.join([f'-{x+1}' for x in body]) + ' 0')

                # If the clause is in evidence:
                #   - This is the selected value, so we must set head to T
                #   - This is not the selected value, so we must set head to F
                if in_evidence[vid]:
                    if selected_values[vid] == vidx:
                        clauses.append(f'{head}')
                        clauses_cnf.append(f'{head+1} 0')
                    else:
                        clauses.append(f'-{head}')
                        clauses.append(f'-{head+1} 0')

    n_probabilistic_var = sum([sum([len(x) for x in v.cpt.entries]) for v in variables])
    n_deterministic_var = sum([len(v.values) for v in variables])
    n_var = n_probabilistic_var + n_deterministic_var

    for target_var in [v for v in variables if v.is_leaf]:
        n_clause = len(clauses) + len(target_var.values)-1
        n_clause_cnf = len(clauses_cnf) + len(target_var.values)-1
        for i, value in enumerate(target_var.value_names):
            fppidimacs = open(os.path.join(_script_dir, 'ppidimacs', outdir,  f'{safe_str_bash(target_var.name)}_{safe_str_bash(value)}.ppidimacs'), 'w')
            fpcnf = open(os.path.join(_script_dir, 'pcnf', outdir, f'{safe_str_bash(target_var.name)}_{safe_str_bash(value)}.cnf'), 'w')

            # HEADER
            fppidimacs.write(f'p cnf {n_var} {n_clause}\n')
            fpcnf.write(f'p cnf {n_var} {n_clause_cnf}\n')
            fpcnf.write(f'c p show {" ".join([str(x+1) for x in range(cpt_var_id)])} 0\n')

            # DISTRIBUTIONS
            fppidimacs.write('\n'.join(distribution_lines) + '\n')
            fpcnf.write('\n'.join(cnf_weights) + '\n')

            # CLAUSES
            fppidimacs.write('\n'.join(clauses) + '\n')
            fpcnf.write('\n'.join(clauses_cnf) + '\n')

            # TARGET PROBA
            for v in target_var.value_names:
                if v != value:
                    fppidimacs.write(f'-{target_var.values[v] + cpt_var_id}\n')
                    fpcnf.write(f'-{target_var.values[v] + cpt_var_id + 1} 0\n')
            
            fppidimacs.close()
            fpcnf.close()

instances = [
        'alarm',
        'andes',
        'asia',
        'cancer',
        'child',
        'earthquake',
        'hailfinder',
        'hepar2',
        'insurance',
        'pigs',
        'sachs',
        'survey',
        'water',
        'win95pts',
]

for name in instances:
    print(f'Processing file {name}')
    variables = parse_network(os.path.join(_script_dir, 'bif', name + '.bif'))
    write_network(name, variables, 0.3)
