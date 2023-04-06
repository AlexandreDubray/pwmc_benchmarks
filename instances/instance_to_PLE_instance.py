import os
import sys

def PLE(infile):
    outfile = infile + '.ple'
    with open(infile, 'r') as fin, open(outfile, 'w') as fout:
        inclauses = fin.readlines()
        s = inclauses[0].rstrip().split(' ')
        nvar = int(s[2])
        nclauses_ple = int(s[3])
        var_clause_map = {}
        deactivated_clauses = set()
        inclauses = inclauses[1:]
        outclauses = []

        parsed_clauses = []
        for i in range(len(inclauses)):
            outclauses.append(inclauses[i])
            if not inclauses[i].startswith('c'):
                cl = []
                for x in inclauses[i].rstrip().split(' '):
                    cl.append(int(x))
                    try:
                        var_clause_map[int(x)].append(len(parsed_clauses))
                    except KeyError:
                        var_clause_map[int(x)] = [len(parsed_clauses)]
                parsed_clauses.append(cl)


        changed = True
        while changed:
            changed = False
            var_pos = [False for _ in range(nvar+1)]
            var_neg = [False for _ in range(nvar+1)]
            for i in range(len(parsed_clauses)):
                if i not in deactivated_clauses:
                    for x in parsed_clauses[i]:
                        if x < 0:
                            var_neg[abs(x)] = True
                        else:
                            var_pos[x] = True

            for v in range(1, nvar+1):
                if var_pos[v] != var_neg[v]:
                    changed = True
                    if var_pos[v]:
                        nclauses_ple += 1
                        outclauses.append(f'{v} 0')
                        for cl in var_clause_map[v]:
                            deactivated_clauses.add(cl)
                    else:
                        nclauses_ple += 1
                        outclauses.append(f'-{v} 0')
                        for cl in var_clause_map[-(v)]:
                            deactivated_clauses.add(cl)
        fout.write(f'p cnf {nvar} {nclauses_ple}\n')
        fout.write('\n'.join(outclauses))

if __name__ == '__main__':
    PLE(sys.argv[1])
