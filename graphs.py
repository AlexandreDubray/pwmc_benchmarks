#! /usr/bin/env python3
import os
import sys
import matplotlib.pyplot as plt

timestamp = sys.argv[1]
old_timestamp = sys.argv[2]
timeout=float(sys.argv[3]) - 0.5
solvers = [sys.argv[i] for i in range(4, len(sys.argv))]
if len(solvers) == 0:
    print("You must specify at least one solver")
    sys.exit(1)

_script_dir = os.path.dirname(os.path.realpath(__file__))
result_dir = os.path.join(_script_dir, 'results', timestamp)
previous_result_dir = os.path.join(_script_dir, 'results', old_timestamp)

problems = ['bn', 'wn']

def parse_time_stderr(stderr_out):
    s = stderr_out.replace('"', '').split('_')
    t = float(s[1]) + float(s[2])
    return t if t < timeout else None

queries = {problem: {} for problem in problems}
old_queries = {problem: {} for problem in problems}

def get_dataset_query_name(instance, problem_type):
    s = instance.split('/')
    if problem_type == 'bn':
        dataset = s[-2]
        query = s[-1].split('_')[0]
    elif problem_type == 'pg':
        dataset = f'{s[-4]}_{s[-3]}'
        query = s[-1].split('_')[0]
    elif problem_type == 'wn':
        ss = s[-1].split('_')
        dataset = ss[0]
        query = '_'.join(ss[1:]).split('.')[0]
    else:
        raise ValueError(f"Wrong problem type {problem_type}")
    return (dataset, query)

def get_solver_runtimes(solver, rdir, queries_dict):
    runtimes = {problem: {} for problem in problems}

    for problem_type in problems:
        try:
            with open(os.path.join(rdir, solver, f'{problem_type}.csv')) as f:
                stderr_index = None
                instance_index = None
                for line in f:
                    if line.rstrip() == '"':
                        continue
                    s = line.rstrip().split(',')
                    if stderr_index is None:
                        stderr_index = s.index('Stderr')
                        instance_index = s.index('V2')
                        continue
                    instance = s[instance_index]
                    (dataset, query) = get_dataset_query_name(instance, problem_type)
                    # Adding the query to the set of problems
                    if dataset not in queries_dict[problem_type]:
                        queries_dict[problem_type][dataset] = set()
                    if query not in queries_dict[problem_type][dataset]:
                        queries_dict[problem_type][dataset].add(query)

                    # computing runtime and adding it to the solver run times
                    if dataset not in runtimes[problem_type]:
                        runtimes[problem_type][dataset] = {query: []}
                    if query not in runtimes[problem_type][dataset]:
                        runtimes[problem_type][dataset][query] = []
                    time = parse_time_stderr(s[stderr_index])
                    if time is not None:
                        runtimes[problem_type][dataset][query].append(time)
        except FileNotFoundError:
            pass
    return runtimes

solvers_runtime = {solver: get_solver_runtimes(solver, result_dir, queries) for solver in solvers}
previous_solvers_runtime = {solver: get_solver_runtimes(solver, previous_result_dir, old_queries) for solver in solvers}

plots_dir = os.path.join(result_dir)
os.makedirs(plots_dir, exist_ok=True)

# For each problem, we create one .md file for each dataset, resuming the run time of the solvers
# for each of its query
solver_times = {solver: [] for solver in solvers}
solver_times_pb = {problem: {solver: [] for solver in solvers} for problem in problems}
for problem in problems:
    pb_dir = os.path.join(plots_dir, problem)
    with open(os.path.join(plots_dir, f'table_{problem}.md'), 'w') as f:
        for dataset in queries[problem]:
            f.write(f'# {dataset}\n\n')
            f.write('|Query|' + '|'.join(solvers) + '|\n')
            f.write('|-----|' + '|'.join(['-'*len(solver) for solver in solvers]) + '|\n')
            solvers_mean_time = [None for _ in solvers]
            solver_diff_previous = [0.0 for _ in solvers]
            solvers_previous_mean_time = [None for _ in solvers]
            for query in queries[problem][dataset]:
                # Get the mean run times for the last set of benchmarks
                for i, solver in enumerate(solvers):
                    if query in solvers_runtime[solver][problem][dataset]:
                        times = solvers_runtime[solver][problem][dataset][query]
                        solvers_mean_time[i] = sum(times)/len(times) if len(times) > 0 else None
                    if solvers_mean_time[i] is not None:
                        solver_times[solver].append(solvers_mean_time[i])
                        solver_times_pb[problem][solver].append(solvers_mean_time[i])
                # Get the mean run times from the previous benchmarks
                for i, solver in enumerate(solvers):
                    if dataset not in previous_solvers_runtime[solver][problem]:
                        solver_diff_previous[i] = "new"
                    else:
                        if query in previous_solvers_runtime[solver][problem][dataset]:
                            times = previous_solvers_runtime[solver][problem][dataset][query]
                            mean_time = sum(times)/len(times) if len(times) > 0 else None
                            if mean_time is None and solvers_mean_time[i] is None:
                                solver_diff_previous[i] = "-"
                            elif mean_time is not None and solvers_mean_time[i] is None:
                                solver_diff_previous[i] = "was solved"
                            elif mean_time is None and solvers_mean_time[i] is not None:
                                solver_diff_previous[i] = "newly solved"
                            else:
                                diff = (solvers_mean_time[i] / mean_time)*100.0 - 100.0
                                solver_diff_previous[i] = "{}{:.2f}%".format("-" if diff < 0 else "+", abs(diff))
                f.write(f'|{query}|')
                f.write('|'.join(['{:.3f}s ({})'.format(x, solver_diff_previous[i]) if x is not None else f'/ ({solver_diff_previous[i]})' for i,x in enumerate(solvers_mean_time)]))
                f.write('|\n')
            f.write('\n')

# Generate all the cactus plots for the problems + a general cactus plot
for pb in problems:
    for solver in solvers:
        x = sorted(solver_times_pb[pb][solver])
        for i in range(1, len(x)):
            x[i] += x[i-1]
        plt.plot(x, [i for i in range(len(x))], label=solver)

    plt.semilogx()
    plt.xlabel("Time in second (log-scale)")
    plt.ylabel("Number of inst. solved")
    plt.legend()
    plt.savefig(os.path.join(plots_dir, f'cactus_{pb}.svg'))
    plt.close()

for solver in solvers:
    x = sorted(solver_times[solver])
    for i in range(1, len(x)):
        x[i] += x[i-1]
    plt.plot(x, [i for i in range(len(x))], label=solver)

plt.semilogx()
plt.xlabel("Time in second (log-scale)")
plt.ylabel("Number of inst. solved")
plt.legend()
plt.savefig(os.path.join(plots_dir, 'cactus.svg'))
plt.close()

with open(os.path.join(plots_dir, 'README.md'), 'a') as f:
    f.write(f'# Plots for the results of benchmark {timestamp}\n\n')
    f.write(f'For details about the instances, see file for a query by query comparison\n')
    f.write('## All instances\n\n')
    for solver in solvers:
        total_instance_solved = sum([len(solver_times_pb[pb][solver]) for pb in problems])
        f.write(f'- {solver} solved {total_instance_solved} in total\n')
    f.write('\n')
    f.write(f'![](./cactus.svg)\n\n')

    for problem in problems:
        f.write(f'## {problem}\n\n')
        f.write(f'- details [here](./table_{problem}.md)\n')
        for solver in solvers:
            nb_instance_solved = len(solver_times_pb[problem][solver])
            f.write(f'- {solver} solved {nb_instance_solved} instances in this problem\n')
        f.write('\n')
        f.write(f'![](./cactus_{problem}.svg)\n\n')
