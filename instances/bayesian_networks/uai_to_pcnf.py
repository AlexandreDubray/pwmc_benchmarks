import os
import itertools
from functools import reduce
import operator
import re

script_dir = os.path.dirname(os.path.realpath(__file__))

def pcnf_encoding(dataset):
    os.makedirs(os.path.join(script_dir, 'pcnf', dataset), exist_ok=True)
    with open(os.path.join(script_dir, 'uai', dataset + '.uai')) as f:
        
        distributions = []
        clauses = []
        
        lines = f.readlines()
        assert(lines[0].rstrip() == 'BAYES')
        
        number_network_vars = int(lines[1])
        # CPT definition starts after:
        #   - BAYES line (1)
        #   - Number of variables in the network (1)
        #   - Domain size of the variables (1)
        #   - Number of CPT (equal to the number of variable) (1)
        #   - Scope of the CPTs (number_network_vars)
        #   - A blank line
        start_cpt = 1 + 1 + 1 + 1 + number_network_vars + 1
        
        # Map for each network variable, and each of its value, the associated deterministic variable
        deterministic_variables = []
        # Size of the domain of each network variable
        domain_size = []
        for d_size in [int(x) for x in lines[2].rstrip().split(' ')]:
            deterministic_variables.append([0 for _ in range(d_size)])
            domain_size.append(d_size)
        # Is the network variable a leaf ?
        is_leaf = [True for _ in range(number_network_vars)]
        # Scope of each CPT
        cpt_scope = []
        for cpt_score_def in lines[4:(4+number_network_vars)]:
            cpt_scope.append([int(x) for x in cpt_score_def.rstrip().split(' ')[1:]])
            # Last varialbe if the target variable of the CPT, hence all other are not leaves
            for variable in cpt_scope[-1][:-1]:
                is_leaf[variable] = False

        # Map for each CPT entry its associated probabilistic variable
        probabilistic_variables = []
        variable_index = 1
        
        # First, we scan the CPTs and look for identical distributions
        for cpt_idx in range(number_network_vars):
            probabilistic_variables.append([])
            probabilities = [float(x) for x in lines[start_cpt + 2*cpt_idx + 1].rstrip().split(' ')]
            target_variable = cpt_scope[cpt_idx][-1]
            parent_variables_dom = reduce(operator.mul, [domain_size[x] for x in cpt_scope[cpt_idx][:-1]], 1) if len(cpt_scope[cpt_idx]) > 1 else 1
            number_distribution = int(len(probabilities) / domain_size[target_variable])
            
            cache = {}
            
            for d in range(number_distribution):
                distribution_proba = [probabilities[d + i*parent_variables_dom] for i in range(domain_size[target_variable])]
                cache_key = tuple(x for x in sorted(distribution_proba))
                
                if cache_key in cache:
                    assigned_variable = cache[cache_key]
                    variables = [0 for _ in range(len(assigned_variable))]
                    ds = sorted([(x, i) for i, x in enumerate(distribution_proba)])
                    for i in range(len(variables)):
                        (proba, initial_id) = ds[i]
                        (cached_proba, variable) = assigned_variable[i]
                        assert(proba == cached_proba)
                        variables[initial_id] = variable
                    probabilistic_variables[-1].append(variables)
                else:
                    is_fixed = len([x for x in distribution_proba if x == 1.0]) != 0
                    if not is_fixed:
                        distributions.append(f'c p distribution {" ".join([str(x) for x in distribution_proba if x != 0.0])}')
                    # If the probability is 0 -> equivalent to setting the associated variable to F
                    # If the probability is 1 -> equivalent to setting the associated variable to T
                    variables = []
                    for p in distribution_proba:
                        if p == 0.0 or p == 1.0:
                            variables.append(None)
                        else:
                            variables.append(variable_index)
                            variable_index += 1
                    probabilistic_variables[-1].append(variables)
                    # updating the cache
                    cache[cache_key] = sorted([(x, y) for x, y in zip(distribution_proba, variables)])

        # Now we give a variable index for each value of each network's variable
        for network_variable_id in range(number_network_vars):
            for i in range(domain_size[network_variable_id]):
                deterministic_variables[network_variable_id][i] = variable_index
                variable_index += 1
        
        # Format for the CPTs:
        #   - first line: the size of the CPT
        #   - second line: the probabilities.
        # The CPT are written with respect to the order defined in their scope, increasing the last variable value.
        # Hence, if the score are X Y Z (in that order), with X, Y and Z boolean variables, the probabilities are given for
        # the tuples (in that order): (X=T, Y=T, Z=T), (X=T,Y=T,Z=F), (X=T,Y=F,Z=T),...
        for cpt_idx in range(number_network_vars):
            # First we generate the list with the domain of the variables in the CPT's scope
            domains = [deterministic_variables[x] for x in cpt_scope[cpt_idx]]
            # Now we generate all combinations
            cpt_entry = list(itertools.product(*domains))
            assert(len(cpt_entry) == int(lines[start_cpt + 2*cpt_idx]))
            # Sort the cpt entries by incrementing the last variable first
            cpt_entry = sorted([tuple(reversed(x)) for x in cpt_entry])
            # put back the variables in the correct order
            cpt_entry = [tuple(reversed(x)) for x in cpt_entry]
            probabilities = [float(x) for x in lines[start_cpt + 2*cpt_idx + 1].rstrip().split(' ')]
            assert(len(cpt_entry) == len(probabilities))
            
            target_variable = cpt_scope[cpt_idx][-1]
            parent_variables_dom = reduce(operator.mul, [domain_size[x] for x in cpt_scope[cpt_idx][:-1]], 1) if len(cpt_scope[cpt_idx]) > 1 else 1
            number_distribution = int(len(probabilities) / domain_size[target_variable])
            
            for d in range(number_distribution):
                distribution_proba = [probabilities[d + i*parent_variables_dom] for i in range(domain_size[target_variable])]
                
                # A clause should be generated for each entry in the CPT
                for i in range(domain_size[target_variable]):
                    if distribution_proba[i] == 0.0:
                        continue
                    variable_values = cpt_entry[i*parent_variables_dom + d]
                    parent_values = variable_values[:-1]
                    target_variable_value = variable_values[-1]
                    # If the distribution probabiility is 0, equivalent to setting the probabilistic variables to F, which is in the implicant
                    # so the clause is always respected
                    # Same for 1, equivalent to setting the variable to T
                    if distribution_proba[i] == 1.0:
                        clauses.append('{} {} 0'.format(
                            " ".join([f"-{x}" for x in parent_values]),
                            f"{target_variable_value}"
                        ))
                    else:
                        p_var = probabilistic_variables[cpt_idx][d][i]
                        clauses.append('{} {} {} 0'.format(
                            " ".join([f"-{x}" for x in parent_values]),
                            f"-{p_var}",
                            f"{target_variable_value}"
                        ))
    
    # Create each query separately
    file_idx = 1
    for network_var in range(number_network_vars):
        if is_leaf[network_var]:
            for value in range(domain_size[network_var]):
                associated_deterministic_var = deterministic_variables[network_var][value]
                
                with open(os.path.join(script_dir, 'pcnf', dataset, f'{file_idx}.cnf'), 'w') as f:
                    f.write(f'p cnf {variable_index} {len(clauses) + domain_size[network_var] - 1}\n')
                    f.write('\n'.join(distributions) + '\n')
                    f.write('\n'.join(clauses) + '\n')
                    for d_var in deterministic_variables[network_var]:
                        if d_var != associated_deterministic_var:
                            f.write(f'-{d_var} 0\n')
                file_idx += 1
    
    # Put all the queries in the same file
    
    with open(os.path.join(script_dir, 'learning', f'{dataset}.cnf'), 'w') as f:
        f.write('\n'.join(distributions) + '\n')
        for network_var in range(number_network_vars):
            if is_leaf[network_var]:
                for value in range(domain_size[network_var]):
                    associated_deterministic_var = deterministic_variables[network_var][value]
                    f.write('c p query\n')
                    f.write(f'p cnf {variable_index} {len(clauses) + domain_size[network_var] - 1}\n')
                    f.write('\n'.join(clauses) + '\n')
                    for d_var in deterministic_variables[network_var]:
                        if d_var != associated_deterministic_var:
                            f.write(f'-{d_var} 0\n')


instances = [f.split('.')[0] for f in os.listdir(os.path.join(script_dir, 'uai')) if os.path.isfile(os.path.join(script_dir, 'uai', f))]

for instance in instances:
    print(instance)
    pcnf_encoding(instance)