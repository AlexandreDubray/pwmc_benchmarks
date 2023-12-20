import os
import itertools
from functools import reduce
import operator
import re
import subprocess

script_dir = os.path.dirname(os.path.realpath(__file__))

def get_network_data(dataset):
    with open(os.path.join(script_dir, 'uai', dataset + '.uai')) as f:
        
        lines = f.readlines()
        assert(lines[0].rstrip() == 'BAYES')
        
        number_network_vars = int(lines[1])

        domain_size = []
        for d_size in [int(x) for x in lines[2].rstrip().split(' ')]:
            domain_size.append(d_size)

        is_leaf = [True for _ in range(number_network_vars)]
        cpt_scope = []
        for cpt_score_def in lines[4:(4+number_network_vars)]:
            for variable in [int(x) for x in cpt_score_def.rstrip().split(' ')[1:-1]]:
                is_leaf[variable] = False
        return {'leaf': is_leaf, 'dom_size': domain_size}

def parse_exe_output():
    output = {}
    with open('tmp.cnf') as f:
        lines = f.readlines()
        s = lines[0].rstrip().split(' ')
        output['nvars'] = int(s[2])
        output['nclauses'] = int(s[3])
        output['clauses'] = lines[1:]
        
    weights = {}
    with open('tmp.weight') as f:
        for line in f.readlines()[:-1]:
            s = line.rstrip().split(' ')
            var = int(s[0])
            weight = float(s[1])
            weights[var] = weight
    output['weights'] = weights
    
    variable_map = {}
    with open('tmp.map') as f:
        for line in f:
            s = line.rstrip().split('=')
            var = int(s[0])
            subsplit = s[1].split('][')
            variable_map[var] = [[int(x) for x in re.findall(r'-?\d+', y)] for y in subsplit]
    output['variable_map'] = variable_map
    return output

def enc1(dataset):
    os.makedirs(os.path.join(script_dir, 'enc1', dataset))
    
def make_enc_encoding(dataset, outdir):
    os.makedirs(os.path.join(outdir, dataset), exist_ok=True)
    output = parse_exe_output()
    network_data = get_network_data(dataset)
    file_idx = 1
    for network_var in range(len(network_data['dom_size'])):
        if network_data['leaf'][network_var]:
            dom_size = network_data['dom_size'][network_var]
            for variable_value in range(dom_size):
                n_clause = output['nclauses'] + len(output['variable_map'][network_var])
                with open(os.path.join(outdir, dataset, f'{file_idx}.cnf'), 'w') as f:
                    f.write(f'p cnf {output["nvars"]} {n_clause}\n')
                    for v in output['weights']:
                        f.write(f'c p weight {v} {output["weights"][v]} 0\n')
                    f.write(''.join(output["clauses"]))
                    
                    for value_indicator_variables in output['variable_map'][network_var][variable_value]:
                        f.write(f'{value_indicator_variables} 0\n')
                file_idx += 1


def make_pysdd_encoding(dataset, outdir):
    os.makedirs(os.path.join(outdir, dataset), exist_ok=True)
    output = parse_exe_output()
    network_data = get_network_data(dataset)
    file_idx = 1
    for network_var in range(len(network_data['dom_size'])):
        if network_data['leaf'][network_var]:
            dom_size = network_data['dom_size'][network_var]
            for variable_value in range(dom_size):
                n_clause = output['nclauses'] + len(output['variable_map'][network_var])
                print(os.path.join(outdir, dataset, f'{file_idx}.cnf'))
                with open(os.path.join(outdir, dataset, f'{file_idx}.cnf'), 'w') as f:
                    weights = ["0.0"]*output['nvars']*2
                    for v in output['weights']:
                        if v > 0:
                            weights[(v-1)*2] = str(output['weights'][v])
                        else:
                            weights[(-v-1)*2+1] = str(output['weights'][v])
                    f.write(f'c weights {" ".join(weights)}\n')
                    f.write(f'p cnf {output["nvars"]} {n_clause-1}\n')
                    f.write(''.join(output["clauses"]))
                    
                    for value_indicator_variables in output['variable_map'][network_var][variable_value]:
                        f.write(f'{value_indicator_variables} 0\n')
                file_idx += 1

def enc3(dataset):
    bash_cmd = ['./bn2cnf_linux', '-i', f'uai/{dataset}.uai', '-o', 'tmp.cnf', '-w', 'tmp.weight', '-v', 'tmp.map']
    subprocess.run(bash_cmd, stdout=subprocess.DEVNULL)
    make_enc_encoding(dataset, os.path.join(script_dir, 'enc3'))

def enc4(dataset):
    bash_cmd = ['./bn2cnf_linux', '-i', f'uai/{dataset}.uai', '-o', 'tmp.cnf', '-w', 'tmp.weight', '-v', 'tmp.map', '-s', 'prime']
    subprocess.run(bash_cmd, stdout=subprocess.DEVNULL)
    make_enc_encoding(dataset, os.path.join(script_dir, 'enc4'))

def enc4linp(dataset):
    bash_cmd = ['./bn2cnf_linux', '-i', f'uai/{dataset}.uai', '-o', 'tmp.cnf', '-w', 'tmp.weight', '-v', 'tmp.map', '-s', 'prime', '-e', 'LOG', '-implicit']
    subprocess.run(bash_cmd, stdout=subprocess.DEVNULL)
    make_enc_encoding(dataset, os.path.join(script_dir, 'enc4linp'))

def pysdd(dataset):
    #based on enc4linp
    bash_cmd = ['./bn2cnf_linux', '-i', f'uai/{dataset}.uai', '-o', 'tmp.cnf', '-w', 'tmp.weight', '-v', 'tmp.map', '-s', 'prime', '-e', 'LOG', '-implicit']
    subprocess.run(bash_cmd, stdout=subprocess.DEVNULL)
    make_pysdd_encoding(dataset, os.path.join(script_dir, 'pysdd'))


instances = [f.split('.')[0] for f in os.listdir(os.path.join(script_dir, 'uai')) if os.path.isfile(os.path.join(script_dir, 'uai', f))]

for instance in instances:
    print(instance)
    enc3(instance)
    enc4(instance)
    enc4linp(instance)
    pysdd(instance) #based on enc4linp

os.remove(os.path.join(script_dir, 'tmp.cnf'))
os.remove(os.path.join(script_dir, 'tmp.weight'))
os.remove(os.path.join(script_dir, 'tmp.map'))
