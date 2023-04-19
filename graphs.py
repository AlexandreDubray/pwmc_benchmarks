#! /usr/bin/env python3
import os
import sys
import matplotlib.pyplot as plt

timestamp = sys.argv[1]
old_timestamp = sys.argv[2]
timeout=float(sys.argv[3])

_script_dir = os.path.dirname(os.path.realpath(__file__))
result_dir = os.path.join(_script_dir, 'results', timestamp)
previous_result_dir = os.path.join(_script_dir, 'results', old_timestamp)

problems = ['bn', 'bn_enc4', 'pg', 'pg_ple', 'wn', 'wn_ple']

def get_run_times(solver, rd, problem):
    runtimes = []
    filepath = os.path.join(rd, solver, problem + '.csv')
    if not os.path.exists(filepath):
        return []
    with open(filepath) as f:
        i = 0
        for line in f:
            if i % 2 != 0:
                time = float(line.split(',')[-1].split('_')[0][1:])
                if time <= timeout:
                    runtimes.append(time)
            i += 1
        return sorted(runtimes)

solvers = {
    'gpmc': {
        'color': 'g',
        'runtimes': {problem: get_run_times('gpmc', result_dir, problem) for problem in problems},
    },
    'projMC': {
        'color': 'r',
        'runtimes': {problem: get_run_times('projMC', result_dir, problem) for problem in problems},
    },
    'schlandals': {
        'color': 'b',
        'runtimes': {problem: get_run_times('schlandals', result_dir, problem) for problem in problems},
    }
}

def get_plot_name(problems):
    return f'cactus_plot_{"_".join(problems)}'

def cactus_plot(problems):
    for solver in solvers:
        solved_time = []
        for problem in problems:
            if problem in solvers[solver]['runtimes']:
                solved_time += solvers[solver]['runtimes'][problem]
        if len(solved_time) > 0:
            max_time = int(max(solved_time))
            if max_time < max(solved_time):
                max_time += 1
            y = [0 for _ in range(max_time+1)]
            for time in solved_time:
                int_time = int(time)
                if int_time < time:
                    int_time += 1
                y[int_time] += 1
            
            for i in range(1, len(y)):
                y[i] += y[i-1]
            color = solvers[solver]['color']
            linestyle = '-'
            if problem.endswith('enc4'):
                linestyle = '--'
            if problem.endswith('_ple'):
                linestyle = ':'
            plt.plot([i for i in range(max_time+1)], y, label=f'{solver}/{problem}', color=color, linestyle=linestyle)
    plt.xlabel('Run time in seconds')
    plt.xlim((0, timeout))
    plt.ylabel('Number of solved instance')
    plt.legend()
    plt.savefig(os.path.join(result_dir, f'{get_plot_name(problems)}.pdf'))
    plt.savefig(os.path.join(result_dir, f'{get_plot_name(problems)}.svg'))

bn_instances = ['bn', 'bn_enc4', 'bn_ple']
pg_instances = ['pg']
wn_instances = ['wn', 'wn_ple']
cactus_plot(bn_instances)
cactus_plot(pg_instances)
cactus_plot(wn_instances)

with open(os.path.join(result_dir, 'README.md'), 'a') as f:
    
    f.write('# Cactus plots for the problems\n')
    f.write('## Bayesian Networks\n')
    plot_fname = f'{get_plot_name(bn_instances)}.svg'
    f.write(f'![](./{plot_fname})\n')

    f.write('## Power Grid Networks\n')
    plot_fname = f'{get_plot_name(pg_instances)}.svg'
    f.write(f'![](./{plot_fname})\n')

    f.write('## Water Networks\n')
    plot_fname = f'{get_plot_name(wn_instances)}.svg'
    f.write(f'![](./{plot_fname})\n')
