#! /usr/bin/env bash
python3 -m pip install --user shapely fiona gdal pyyaml
echo "Generating the input files from the data sets"
echo "Generating power transmission grid data files"
python3 instances/power_transmission_grid/split_europe.py
echo "Generating USA transmission grid data files"
python3 instances/power_transmission_grid/split_usa.py
python3 instances/power_transmission_grid/generate_inputs.py
echo "Generating bayesian network data files"
python3 instances/bayesian_networks/bif_to_pcnf.py
echo "Generating water supply network data files"
python3 instances/water-supply-network/parse_networks.py
