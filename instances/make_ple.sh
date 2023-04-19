nthreads=50
parallel -j $nthreads python3 instance_to_PLE_instance.py {} true ::: $(find bayesian_networks/pcnf/ -type f -name '*.cnf')
parallel -j $nthreads python3 instance_to_PLE_instance.py {} true ::: $(find water-supply-network/ -type f -name '*.cnf')
parallel -j $nthreads python3 instance_to_PLE_instance.py {} false ::: $(find bayesian_networks/pcnf/ -type f -name '*.ppidimacs')
parallel -j $nthreads python3 instance_to_PLE_instance.py {} false ::: $(find water-supply-network/ -type f -name '*.ppidimacs')
