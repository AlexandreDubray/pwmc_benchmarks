import random
import re
import os
import numpy as np

random.seed(862453179)

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
    os.makedirs(f'ppidimacs/{outdir}', exist_ok=True)
    os.makedirs(f'pcnf/{outdir}', exist_ok=True)
    in_evidence = [not v.is_leaf and random.random() <= prop_evidence for v in variables]
    selected_values = [random.randint(0, len(v.values) - 1) for v in variables]

    # normalization of the CPT given the evidences
    evidences = {}
    for i, var in enumerate(variables):
        if in_evidence[i]:
            selected_value = selected_values[i]
            evidences[var.name] = selected_value
            for j in range(len(var.cpt.entries)):
                var.cpt.entries[j] = [0.0 if x != selected_value else 1.0 for x in range(len(var.value_names))]

    n_probabilistic_var = sum([sum([len(x) for x in v.cpt.entries]) for v in variables])
    n_deterministic_var = sum([len(v.values) for v in variables])
    n_var = n_probabilistic_var + n_deterministic_var

    n_clause_cpt = n_probabilistic_var # one clause per entry in a cpt

    additional_clause_pcnf = 0
    for vid, v in enumerate(variables):
        additional_clause_pcnf += len(v.cpt.entries)
        for didx in range(len(v.cpt.entries)):
            for i in range(len(v.values)):
                if v.cpt.entries[didx][i] == 0.0:
                    additional_clause_pcnf += 1
                for j in range(i+1, len(v.values)):
                          additional_clause_pcnf += 1

    for target_var in [v for v in variables if v.is_leaf]:
        n_clause = n_clause_cpt + len(target_var.values)-1
        for i, value in enumerate(target_var.value_names):
            fout = open(f'ppidimacs/{outdir}/{target_var.name}_{value}.ppidimacs', 'w')
            fpcnf = open(f'pcnf/{outdir}/{target_var.name}_{value}.cnf', 'w')
            fout.write(f'p cnf {n_var} {n_clause}\n')
            fpcnf.write(f'p pcnf {n_var} {n_clause + additional_clause_pcnf} {n_probabilistic_var}\n')
            
            deterministic_var_offset = 0
            fout.write(f'c --- DISTRIBUTIONS ---\n')
            cpt_var_id = 0
            for var in variables:
                fout.write(f'c Distributions of var {var.name}\n')
                fout.write(f'c {" ".join(var.value_names)}\n')
                for distribution in var.cpt.entries:
                    fout.write('d ' + ' '.join(['{}'.format(x) for x in distribution]) + '\n')
                    var.cpt.ppidimacs_var.append([cpt_var_id + i for i in range(len(var.values))])
                    cpt_var_id = var.cpt.ppidimacs_var[-1][-1] + 1
            fout.write(f'c --- END DISTRIBUTIONS ---\n')

            fpcnf.write(f'vp {" ".join([str(x+1) for x in range(cpt_var_id)])} 0\n')

            fout.write(f'c --- Deterministic variables ---\n')
            for var in variables:
                var_line = [f'{x} {var.values[x] + cpt_var_id}' for x in var.value_names]
                fout.write(f'c {var.name} {" ".join(var_line)}\n')
                
            fout.write('c --- CLAUSES ---\n')
            for vid, var in enumerate(variables):
                for didx in range(len(var.cpt.entries)):
                    parent_var_ids = var.cpt.parent_domains[didx]

                    fpcnf.write(f'{" ".join([str(x+1) for x in var.cpt.ppidimacs_var[didx]])} 0\n')
                    for i in range(len(var.cpt.ppidimacs_var[didx])):
                        for j in range(i+1, len(var.cpt.ppidimacs_var[didx])):
                            v1 = var.cpt.ppidimacs_var[didx][i]
                            v2 = var.cpt.ppidimacs_var[didx][j]
                            fpcnf.write(f'-{v1+1} -{v2+1} 0\n')

                    for vidx in range(len(var.values)):
                        head = var.get_var_from_id(vidx) + cpt_var_id
                        body = [cpt_var_id + x for x in parent_var_ids] + [var.cpt.ppidimacs_var[didx][vidx]]
                        fout.write(f'{head} ')
                        fout.write(' '.join([f'-{x}' for x in body]))
                        fout.write('\n')
                        
                        fpcnf.write(f'{head+1} ')
                        fpcnf.write(' '.join([f'-{x+1}' for x in body]))
                        fpcnf.write(' 0\n')

                        if var.cpt.entries[didx][vidx] == 0.0:
                            fpcnf.write(f'-{var.cpt.ppidimacs_var[didx][vidx]+1} 0\n')



            fout.write('c --- TARGET PROBABILITY ---\n')
            for v in target_var.value_names:
                if v != value:
                    fout.write(f'-{target_var.values[v] + cpt_var_id}\n')
                    fpcnf.write(f'-{target_var.values[v] + cpt_var_id + 1} 0\n')
            
            fout.close()
            fpcnf.close()

test=False
if not test:
    for file in os.listdir('bif'):
        name = file.split('.')[0]
        print(f'Processing file {name}')
        variables = parse_network(f"bif/{file}")
        write_network(name, variables, 0.3)
else:
    variables = parse_network(f"test.bif")
    write_network("test", variables, 0.0)
