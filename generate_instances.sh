#! /usr/bin/env bash
echo "Generating the input files from the data sets"
echo "Generating power transmission grid data files"
python instances/power_transmission_grid/split_europe.py
python instances/power_transmission_grid/generate_inputs.py
echo "Generating bayesian network data files"
python instances/bayesian_networks/instances_from_bif.py
