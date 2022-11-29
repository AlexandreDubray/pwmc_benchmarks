#! /usr/bin/env bash
python3 -m pip install --user shapely fiona gdal
echo "Generating the input files from the data sets"
echo "Generating power transmission grid data files"
python3 instances/power_transmission_grid/split_europe.py
echo "Generating USA transmission grid data files"
python3 instances/power_transmission_grid/split_usa.py
python3 instances/power_transmission_grid/generate_inputs.py
echo "Generating bayesian network data files"
python3 instances/bayesian_networks/instances_from_bif.py
