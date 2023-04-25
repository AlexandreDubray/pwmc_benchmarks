import os
import itertools
import re

script_dir = os.path.dirname(os.path.realpath(__file__))

def remove_trailing_space(l):
    for i in range(len(l)):
        l[i] = l[i].replace('  ', ' ')

def parse_file(dataset):
    evidence = {}
    with open(os.path.join(script_dir, 'uai', dataset + '.evid')) as f:
        for line in f:
            s = line.rstrip().split(' ')
            if len(s) > 0:
                evidence[int(s[0])] = int(s[1])
    with open(os.path.join(script_dir, 'uai', dataset + '.uai')) as f:
        all_file = f.read().replace('  ', ' ')
        lines = all_file.split('\n')[1:]
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
        is_leaf = [True for _ in range(nvar)]
        for i in range(ncpt):
            vs = lines[idx].rstrip().split(' ')[1:]
            for x in vs[:-1]:
                is_leaf[int(x)] = False
            idx += 1
            cpts_def.append([int(x) for x in vs])

        idx += 1 # blank line

        probabilistic_index = 0
        map_weight = {}
        proba_vars = [[] for v in range(len(variables))]
        cpt_idx = 0
        distributions_clauses = []
        for i in range(idx+1, len(lines), 2):
            probas = [float(x) for x in lines[i].split(' ')]
            distributions = []
            v = cpts_def[cpt_idx][-1]
            cpt_idx += 1
            dom_size = len(variables[v])
            ds = []
            for nd in range(int(len(probas) / dom_size)):
                ds.append([x for x in probas[nd*dom_size:(nd+1)*dom_size]])
            nb_proba_index_needed = 0
            for i in range(len(ds)):
                d = ds[i]
                found_idx = None
                for j in range(max(0, i-1), i):
                    if sorted(ds[i]) == sorted(ds[j]):
                        found_idx = j
                        break
                if found_idx is not None:
                    used_idx = set()
                    dline = []
                    for p in d:
                        for lidx in range(len(proba_vars[v][found_idx])):
                            if lidx not in used_idx:
                                if p == map_weight[proba_vars[v][found_idx][lidx]]:
                                    used_idx.add(lidx)
                                    dline.append(proba_vars[v][found_idx][lidx])
                    proba_vars[v].append(dline)
                else:
                    dline = []
                    for p in d:
                        dline.append(probabilistic_index)
                        map_weight[probabilistic_index] = p
                        probabilistic_index += 1
                    distributions_clauses.append(f'd {" ".join([str(x) for x in d])}')
                    proba_vars[v].append(dline)
        
        deterministic_index = probabilistic_index
        for v in range(len(variables)):
            for i in range(len(variables[v])):
                variables[v][i] = deterministic_index
                deterministic_index += 1
        
        cpt = []
        distributions_m = {}
        for v in range(nvar):
            dom_size = len(variables[v])
            ttt = [variables[x] for x in cpts_def[v]]
            body_vars = list(itertools.product(*ttt))
            idx += 1
            probas = [float(x) for x in lines[idx].rstrip().split(' ')]
                       
            idx += 1
            c = []
            for i in range(len(probas)):
                tt = [x for x in body_vars[i]]
                p = probas[i]
                try:
                    distributions_m[tuple([v] + tt[:-1])].append((tt[-1], proba_vars[v][int(i / dom_size)][i % dom_size], p))
                except KeyError:
                    distributions_m[tuple([v] + tt[:-1])] = [(tt[-1], proba_vars[v][int(i / dom_size)][i % dom_size], p)]
            cpt.append(c)

        # Handling enc4 format
        enc4_tpl_dir = os.path.join(script_dir, 'enc4_tpl')
        cnf_enc4 = open(os.path.join(enc4_tpl_dir, dataset + '.cnf')).readlines()
        enc4_nb_var = abs(int(open(os.path.join(enc4_tpl_dir, dataset + '.weights')).readlines()[-2].split(' ')[0]))
        enc4_header = cnf_enc4[0]
        enc4_clauses = cnf_enc4[1:]
        enc4_weights = []
        enc4_prob_offset = 0
        for v in variables:
            enc4_prob_offset += len(v)
        with open(os.path.join(enc4_tpl_dir, dataset + '.weights')) as fw:
            for line in fw.readlines()[:-1]:
                s = line.rstrip().split(' ')
                var = int(s[0])
                enc4_weights.append(f'c p weight {s[0]} {s[1]} 0')
            
        enc4_mvar = [None for _ in range(nvar)]
        with open(os.path.join(enc4_tpl_dir, dataset + '.map')) as fm:
            for line in fm:
                s = line.split(' ')
                enc4_mvar[int(s[0])] = [int(x) for x in re.findall(r'\d+', line.split(' ')[2])]

        # Writing ppidimacs-like files

        clauses = []
        clauses_cnf = []
        cnf_weights = []
        clauses_enc1 = []
        enc1_weight = []
        
        for evid in evidence:
            for i in range(len(variables[evid])):
                if i != evidence[evid]:
                    clauses.append(f'-{variables[evid][i]}')
                    clauses_cnf.append(f'-{variables[evid][i] + 1} 0')
        
        for vidx in map_weight:
            cnf_weights.append(f'c p weight {vidx + 1} {map_weight[vidx]:.9f} 0')
            enc1_weight.append(f'c p weight {vidx + 1} {map_weight[vidx]:.9f} 0')
            cnf_weights.append(f'c p weight -{vidx + 1} {(1 - map_weight[vidx]):.9f} 0')
            enc1_weight.append(f'c p weight -{vidx + 1} 1.0 0')
            
        for v in variables:
            for vv in v:
                enc1_weight.append(f'c p weight {vv + 1} 1.0 0')
                enc1_weight.append(f'c p weight -{vv + 1} 1.0 0')
        
        for sub_body in distributions_m:
            distrib_idx = tuple([y for x,y,z in distributions_m[sub_body]])
            for end_body, proba_var_idx, proba in distributions_m[sub_body]:
                clauses.append(f'{end_body} {" ".join([str(-x) for x in sub_body[1:]])} -{proba_var_idx}')
                clauses_cnf.append(f'{end_body + 1} {" ".join([str(-(x+1)) for x in sub_body[1:]])} -{proba_var_idx + 1} 0')

                clauses_enc1.append(f'-{end_body + 1} {" ".join([str(-(x+1)) for x in sub_body[1:]])} {proba_var_idx + 1} 0')
                clauses_enc1.append(f'{end_body + 1} -{proba_var_idx + 1} 0')
                for x in sub_body[1:]:
                    clauses_enc1.append(f'{x + 1} -{proba_var_idx + 1} 0')
                
        
        for vs in variables:
            clauses_cnf.append(f'{" ".join([str(x+1) for x in vs])} 0')
            clauses_enc1.append(f'{" ".join([str(x+1) for x in vs])} 0')
            for i in range(len(vs)):
                for j in range(i+1, len(vs)):
                    clauses_cnf.append(f'-{vs[i] + 1} -{vs[j] + 1} 0')
                    clauses_enc1.append(f'-{vs[i] + 1} -{vs[j] + 1} 0')
            
        os.makedirs(os.path.join(script_dir, 'ppidimacs', dataset), exist_ok=True)
        os.makedirs(os.path.join(script_dir, 'pcnf', dataset), exist_ok=True)
        os.makedirs(os.path.join(script_dir, 'enc4', dataset), exist_ok=True)
        os.makedirs(os.path.join(script_dir, 'enc1', dataset), exist_ok=True)
        file_idx = 0
        remove_trailing_space(distributions_clauses)
        remove_trailing_space(clauses)
        remove_trailing_space(clauses_cnf)
        remove_trailing_space(cnf_weights)
        remove_trailing_space(enc4_weights)
        remove_trailing_space(enc4_clauses)
        remove_trailing_space(clauses_enc1)
        for i in range(nvar):
            if is_leaf[i]:
                dom_size = len(variables[i])
                for j in range(len(variables[i])):
                    with open(os.path.join(script_dir, 'ppidimacs', dataset, f'{file_idx}.ppidimacs'), 'w') as fout:
                        fout.write(f'p cnf {deterministic_index} {len(clauses) + dom_size - 1}\n')
                        fout.write('\n'.join(distributions_clauses) + '\n')
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
                                fout.write(f'-{variables[i][k] + 1} 0\n')
                    
                    with open(os.path.join(script_dir, 'enc1', dataset, f'{file_idx}.cnf'), 'w') as fout:
                        fout.write(f'p cnf {deterministic_index} {len(clauses_enc1) + 1}\n')
                        fout.write('\n'.join(enc1_weight) + '\n')
                        fout.write('\n'.join(clauses_enc1) + '\n')
                        fout.write(f'{variables[i][j] + 1} 0\n')

                    with open(os.path.join(script_dir, 'enc4', dataset, f'{file_idx}.cnf'), 'w') as fout:
                        fout.write(f'p cnf {enc4_nb_var} {len(enc4_clauses) + dom_size - 1}\n')
                        fout.write('\n'.join(enc4_weights) + '\n')
                        fout.write(''.join(enc4_clauses))
                        for k in range(len(variables[i])):
                            if k != j:
                                fout.write(f'-{enc4_mvar[i][k]} 0\n')
                        for evid in evidence:
                            for k in range(len(variables[evid])):
                                if k != evidence[evid]:
                                    fout.write(f'-{enc4_mvar[evid][k] + 1} 0\n')
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
    print(instance)
    parse_file(instance)
