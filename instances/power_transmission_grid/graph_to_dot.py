import sys
import os

area = sys.argv[1]
sub_area = sys.argv[2]
source = sys.argv[3]
target = sys.argv[4]

with open('graph.dot', 'w') as f:
    f.write(f'graph {sub_area} {{' + '\n')
    f.write(f'{source} [color="green", style="filled"]\n')
    f.write(f'{target} [color="red", style="filled"]\n')

    with open(f'{area}/{sub_area}/gridkit_{sub_area}-highvoltage-links.csv') as fnodes:
        first = True
        for line in fnodes:
            if first:
                first = False
                continue
            s =  line.split(',')
            source = int(s[1])
            target = int(s[2])
            f.write(f'\t{source} -- {target};\n')

    f.write('}')
