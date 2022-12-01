#! /usr/bin/env python3
import os
import sys
import matplotlib.pyplot as plt

timestamp = sys.argv[1]
timeout=float(sys.argv[2]) - 0.5
solvers = [sys.argv[i] for i in range(3, len(sys.argv))]
if len(solvers) == 0:
    print("You must specify at least one solver")
    sys.exit(1)

_script_dir = os.path.dirname(os.path.realpath(__file__))
result_dir = os.path.join(_script_dir, 'results', timestamp)

problems = ['bn', 'pg']

def parse_time_stderr(stderr_out):
    s = stderr_out.split('_')
    t = float(s[1]) + float(s[2])
    return t if t < timeout else None

queries = {problem: {} for problem in problems}

def get_solver_runtimes(solver):
    runtimes = {problem: {} for problem in problems}

    for problem_type in problems:
        with open(os.path.join(result_dir, solver, f'{problem_type}.csv')) as f:
            stderr_index = None
            instance_index = None
            for line in f:
                if line.rstrip() == '"':
                    continue
                s = line.rstrip().split(',')
                if stderr_index is None:
                    stderr_index = s.index('Stderr')
                    instance_index = s.index('V1')
                    continue
                instance = s[instance_index]
                instance_s = instance.split('/')
                if problem_type == 'bn':
                    dataset = instance_s[-2]
                elif problem_type == 'pg':
                    dataset = f'{instance_s[-4]}_{instance_s[-3]}'
                query = instance_s[-1].split('.')[0]
                # Adding the query to the set of problems
                if dataset not in queries[problem_type]:
                    queries[problem_type][dataset] = set()
                if query not in queries[problem_type][dataset]:
                    queries[problem_type][dataset].add(query)

                # computing runtime and adding it to the solver run times
                if dataset not in runtimes[problem_type]:
                    runtimes[problem_type][dataset] = {query: []}
                if query not in runtimes[problem_type][dataset]:
                    runtimes[problem_type][dataset][query] = []
                time = parse_time_stderr(s[stderr_index])
                if time is not None:
                    runtimes[problem_type][dataset][query].append(time)
    return runtimes

solvers_runtime = {solver: get_solver_runtimes(solver) for solver in solvers}

plots_dir = os.path.join(result_dir, 'plots')
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
            for query in queries[problem][dataset]:
                for i, solver in enumerate(solvers):
                    if query in solvers_runtime[solver][problem][dataset]:
                        times = solvers_runtime[solver][problem][dataset][query]
                        solvers_mean_time[i] = sum(times)/len(times) if len(times) > 0 else None
                    else:
                        solvers_mean_time[i] = None
                    if solvers_mean_time[i] is not None:
                        solver_times[solver].append(solvers_mean_time[i])
                        solver_times_pb[problem][solver].append(solvers_mean_time[i])
                f.write(f'|{query}|' + '|'.join(['{:.3f}s'.format(x) if x is not None else '/' for x in solvers_mean_time]) + '|\n')
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

with open(os.path.join(plots_dir, 'cactus.md'), 'w') as f:
    f.write(f'# Plots for the results of benchmark {timestamp}\n\n')
    f.write(f'For details about the instances, see file for a query by query comparison\n')
    f.write('## All instances\n')
    f.write(f'![](./cactus.svg)\n')

    for problem in problems:
        f.write(f'## {problem}\n')
        f.write(f'![](./cactus_{problem}.svg)\n')
