import sys
from pgmpy.readwrite import BIFReader, UAIReader
from pgmpy.inference import VariableElimination

print("Loading")
reader = BIFReader(sys.argv[1])
#reader = UAIReader(sys.argv[1])
print("Getting the model")
model = reader.get_model()
print("Querying")
inference = VariableElimination(model)
query = inference.query([sys.argv[2]])
print(query)
