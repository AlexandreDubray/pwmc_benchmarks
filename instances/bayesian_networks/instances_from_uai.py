import os
import itertools
import random
import re

script_dir = os.path.dirname(os.path.realpath(__file__))
random.seed(862453179)

def parse_file(dataset):
    with open(os.path.join(script_dir, 'uai', dataset + '.uai')) as f:
        lines = f.readlines()[1:]
        idx = 0
        nvar = int(lines[idx])
        idx += 1
        variables = []
        s = lines[idx].rstrip().split(' ')
        idx += 1
        for i in range(nvar):
            dom_size = int(s[i])
            variables.append([-1 for _ in range(dom_size)])
        ncpt = int(lines[idx])
        idx += 1
        cpts_def = []
        deterministic_index = 0
        is_leaf = [True for _ in range(nvar)]
        for i in range(ncpt):
            vs = lines[idx].rstrip().split(' ')[1:]
            for x in vs[:-1]:
                is_leaf[int(x)] = False
            idx += 1
            cpts_def.append([int(x) for x in vs])
            offset = 1
            for v in cpts_def[-1]:
                offset *= len(variables[v])
            deterministic_index += offset
        for v in range(nvar):
            for i in range(len(variables[v])):
                variables[v][i] = deterministic_index
                deterministic_index += 1
                
        in_evidence = [False for _ in range(nvar)]
        selected_values = [0 for _ in range(nvar)]
        for x in range(nvar):
            if not is_leaf[x] and random.random() < 0.3:
                in_evidence[x] = True
                selected_values[x] = random.choice(variables[x])
        
        idx += 1 # blank line
        cpt = []
        distributions_m = {}
        for v in range(nvar):
            dom_size = len(variables[v])
            ttt = [variables[x] for x in cpts_def[v]]
            ttt.reverse()
            body_vars = list(itertools.product(*ttt))
            idx += 1
            probas = [float(x) for x in lines[idx].rstrip().split(' ')]
            idx += 1
            c = []
            for i in range(len(probas)):
                tt = [x for x in body_vars[i]]
                tt.reverse()
                p = probas[i]
                if in_evidence[v]:
                    if selected_values[v] == tt[-1]:
                        p = 1.0
                    else:
                        p = 0.0
                try:
                    distributions_m[tuple([v] + tt[:-1])].append((tt[-1], p))
                except KeyError:
                    distributions_m[tuple([v] + tt[:-1])] = [(tt[-1], p)]
            cpt.append(c)

        # Handling enc4 format
        enc4_tpl_dir = os.path.join(script_dir, 'enc4_tpl')
        cnf_enc4 = open(os.path.join(enc4_tpl_dir, dataset + '.cnf')).readlines()
        enc4_nb_var = abs(int(open(os.path.join(enc4_tpl_dir, dataset + '.weights')).readlines()[-2].split(' ')[0]))
        enc4_header = cnf_enc4[0]
        enc4_clauses = cnf_enc4[1:]
        enc4_weights = []
        with open(os.path.join(enc4_tpl_dir, dataset + '.weights')) as fw:
            for line in fw:
                enc4_weights.append(f'c p weight {line.rstrip()} 0')
        enc4_prob_offset = 0
        for v in variables:
            enc4_prob_offset += len(v)
            
        enc4_mvar = []
        with open(os.path.join(enc4_tpl_dir, dataset + '.map')) as fm:
            for line in fm:
                enc4_mvar.append([int(x) for x in re.findall(r'\d+', line.split(' ')[2])])

            
        for vidx in range(len(variables)):
            if in_evidence[vidx]:
                sv = selected_values[vidx]
                for i in range(len(variables[vidx])):
                    if variables[vidx] == sv:
                        enc4_clauses.append(f'{enc4_mvar[vidx][i]} 0')
                
        # Writing ppidimacs-like files

        distributions = []
        clauses = []
        clauses_cnf = []
        cnf_weights = []
        probabilistic_index = 0
        
        for sub_body in distributions_m:
            distributions.append(f'd {" ".join([f"{y:.5f}" for x,y in distributions_m[sub_body]])}')
            for end_body, proba in distributions_m[sub_body]:
                clauses.append(f'{end_body} {" ".join([str(-x) for x in sub_body[1:]])} -{probabilistic_index}')
                clauses_cnf.append(f'{end_body + 1} {" ".join([str(-(x+1)) for x in sub_body[1:]])} -{probabilistic_index+1} 0')
                cnf_weights.append(f'c p weight {probabilistic_index + 1} {proba:.5f} 0')
                cnf_weights.append(f'c p weight -{probabilistic_index + 1} {(1-proba):.5f} 0')
                probabilistic_index += 1
        
        for vs in variables:
            clauses_cnf.append(f'{" ".join([str(x+1) for x in vs])} 0')
            for i in range(len(vs)):
                for j in range(i+1, len(vs)):
                    clauses_cnf.append(f'-{vs[i] + 1} -{vs[j] + 1} 0')
            
        os.makedirs(os.path.join(script_dir, 'ppidimacs', dataset), exist_ok=True)
        os.makedirs(os.path.join(script_dir, 'pcnf', dataset), exist_ok=True)
        os.makedirs(os.path.join(script_dir, 'enc4', dataset), exist_ok=True)
        file_idx = 0
        for i in range(nvar):
            if is_leaf[i]:
                dom_size = len(variables[i])
                for j in range(len(variables[i])):
                    with open(os.path.join(script_dir, 'ppidimacs', dataset, f'{file_idx}.ppidimacs'), 'w') as fout:
                        fout.write(f'p cnf {deterministic_index} {len(clauses) + dom_size - 1}\n')
                        fout.write('\n'.join(distributions) + '\n')
                        fout.write('\n'.join(clauses) + '\n')
                        for k in range(len(variables[i])):
                            if k != j:
                                fout.write(f'-{variables[i][k]}\n')

                    with open(os.path.join(script_dir, 'pcnf', dataset, f'{file_idx}.cnf'), 'w') as fout:
                        fout.write(f'p cnf {deterministic_index} {len(clauses_cnf) + dom_size - 1}\n')
                        fout.write(f'c p show {" ".join([str(x + 1) for x in range(probabilistic_index)])} 0\n')
                        fout.write('\n'.join(cnf_weights) + '\n')
                        fout.write('\n'.join(clauses_cnf) + '\n')
                        for k in range(len(variables[i])):
                            if k != j:
                                fout.write(f'-{variables[i][k] + 1}\n')
                                

                    with open(os.path.join(script_dir, 'enc4', dataset, f'{file_idx}.cnf'), 'w') as fout:
                        fout.write(f'p cnf {enc4_nb_var} {len(enc4_clauses) + dom_size - 1}\n')
                        fout.write('\n'.join(enc4_weights) + '\n')
                        fout.write(''.join(enc4_clauses))
                        for k in range(len(variables[i])):
                            if k != j:
                                fout.write(f'-{enc4_mvar[i][k]}\n')
                    file_idx += 1
        
            
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

for instance in instances:
    parse_file(instance)