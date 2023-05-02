import os
import itertools
import re

script_dir = os.path.dirname(os.path.realpath(__file__))

def parse_enc4_template(tpl_dir, dataset, nvar):
    cnf = open(os.path.join(tpl_dir, dataset + '.cnf')).readlines()
    sheader = cnf[0].split(' ')
    clauses = cnf[1:]
    map_var = [None for _ in range(nvar)]
    weights = []

    with open(os.path.join(tpl_dir, dataset + '.weights')) as fw:
        for line in fw.readlines()[:-1]:
            s = line.rstrip().split(' ')
            weights.append(f'c p weight {s[0]} {s[1]} 0')

    with open(os.path.join(tpl_dir, dataset + '.map')) as fm:
        for line in fm:
            s = line.rstrip().split('=')
            v = int(s[0])
            ss = s[1].split('][')
            map_var[v] = [[int(x) for x in re.findall(r'-?\d+', y)] for y in ss]
    return {
            'nvar': int(sheader[2]),
            'clauses': clauses,
            'weights': weights,
            'map_var': map_var
            }


def remove_trailing_space(l):
    for i in range(len(l)):
        l[i] = l[i].replace('  ', ' ')

def parse_file(dataset):
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
        pcnf_exlusive = []
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
                    pcnf_exlusive.append([x for x in dline])
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
        enc4 = parse_enc4_template(os.path.join(script_dir, 'enc4_tpl'), dataset, nvar)
        enc4log = parse_enc4_template(os.path.join(script_dir, 'enc4_log_tpl'), dataset, nvar)
        enc3 = parse_enc4_template(os.path.join(script_dir, 'enc3_tpl'), dataset, nvar)

        # Writing ppidimacs-like files

        clauses = []
        clauses_cnf = []
        cnf_weights = []

        for vidx in map_weight:
            cnf_weights.append(f'c p weight {vidx + 1} {map_weight[vidx]:.9f} 0')
            cnf_weights.append(f'c p weight -{vidx + 1} {(1 - map_weight[vidx]):.9f} 0')

        for sub_body in distributions_m:
            distrib_idx = tuple([y for x,y,z in distributions_m[sub_body]])
            for end_body, proba_var_idx, proba in distributions_m[sub_body]:
                clauses.append(f'{end_body} {" ".join([str(-x) for x in sub_body[1:]])} -{proba_var_idx}')
                clauses_cnf.append(f'{end_body + 1} {" ".join([str(-(x+1)) for x in sub_body[1:]])} -{proba_var_idx + 1} 0')

        for vs in variables:
            clauses_cnf.append(f'{" ".join([str(x+1) for x in vs])} 0')
            for i in range(len(vs)):
                for j in range(i+1, len(vs)):
                    clauses_cnf.append(f'-{vs[i]+1} -{vs[j]+1} 0')

        for excls in pcnf_exlusive:
            clauses_cnf.append(f'{" ".join([str(x+1) for x in excls])} 0')
            for i in range(len(excls)):
                for j in range(i+1, len(excls)):
                    clauses_cnf.append(f'-{excls[i] + 1} -{excls[j] + 1} 0')

        os.makedirs(os.path.join(script_dir, 'ppidimacs', dataset), exist_ok=True)
        os.makedirs(os.path.join(script_dir, 'pcnf', dataset), exist_ok=True)
        os.makedirs(os.path.join(script_dir, 'enc4', dataset), exist_ok=True)
        os.makedirs(os.path.join(script_dir, 'enc3', dataset), exist_ok=True)
        os.makedirs(os.path.join(script_dir, 'enc4_log', dataset), exist_ok=True)
        file_idx = 0
        remove_trailing_space(distributions_clauses)
        remove_trailing_space(clauses)
        remove_trailing_space(clauses_cnf)
        remove_trailing_space(cnf_weights)
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

                    with open(os.path.join(script_dir, 'enc3', dataset, f'{file_idx}.cnf'), 'w') as fout:
                        fout.write(f'p cnf {enc3["nvar"]} {len(enc3["clauses"]) + len(enc3["map_var"][i][j])}\n')
                        fout.write('\n'.join(enc3["weights"]) + '\n')
                        fout.write(''.join(enc3["clauses"]))
                        for x in enc3["map_var"][i][j]:
                            fout.write(f'{x} 0')
                    
                    with open(os.path.join(script_dir, 'enc4', dataset, f'{file_idx}.cnf'), 'w') as fout:
                        fout.write(f'p cnf {enc4["nvar"]} {len(enc4["clauses"]) + len(enc4["map_var"][i][j])}\n')
                        fout.write('\n'.join(enc4["weights"]) + '\n')
                        fout.write(''.join(enc4["clauses"]))
                        for x in enc4["map_var"][i][j]:
                            fout.write(f'{x} 0')

                    with open(os.path.join(script_dir, 'enc4_log', dataset, f'{file_idx}.cnf'), 'w') as fout:
                        fout.write(f'p cnf {enc4log["nvar"]} {len(enc4log["clauses"]) + len(enc4["map_var"][i][j])}\n')
                        fout.write('\n'.join(enc4log["weights"]) + '\n')
                        fout.write(''.join(enc4log["clauses"]))
                        for x in enc4log["map_var"][i][j]:
                            fout.write(f'{x} 0')
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
