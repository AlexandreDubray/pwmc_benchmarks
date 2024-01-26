import sys
from pgmpy.readwrite import BIFReader
from pgmpy.inference import VariableElimination
import os

os.makedirs(os.path.join('.', 'network_probas'), exist_ok=True)
for file in os.listdir('./bif'):
    print(f"Handling {file}")
    with open(os.path.join('network_probas', file.split('.')[0] + '.proba'), 'w') as f:
        f.write('Variable,Value,Proba\n')
        reader = BIFReader(os.path.join('bif', file))
        model = reader.get_model()
        for n in model.get_leaves():
            inference = VariableElimination(model)
            query = inference.query([n])
            for i in range(len(query.values)):
                f.write(f'{n},{query.state_names[n][i]},{query.values[i]}\n')
