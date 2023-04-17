from pgmpy.readwrite import BIFReader, UAIWriter
import os

_script_dir = os.path.dirname(os.path.realpath(__file__))
bif_dir = os.path.join(_script_dir, 'bif')
uai_dir = os.path.join(_script_dir, 'uai')

for f in os.listdir(bif_dir):
    model = BIFReader(os.path.join(bif_dir, f)).get_model()
    outfile = f.split('.')[0] + ".uai"
    UAIWriter(model).write_uai(os.path.join(uai_dir, outfile))