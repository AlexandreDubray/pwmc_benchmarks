parallel -j 50 python3 instance_to_PLE_instance.py {} ::: $(find bayesian_networks/pcnf/ -type f -name '*.cnf')
parallel -j 50 python3 instance_to_PLE_instance.py {} ::: $(find power_transmission_grid/ -type f -name '*.cnf')
parallel -j 50 python3 instance_to_PLE_instance.py {} ::: $(find water-supply-network/ -type f -name '*.cnf')
