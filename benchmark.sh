#! /usr/bin/env bash

# Installs the solvers if not present in the PATH
if ! [ -x "$(command -v ganak)" ]
then
    echo "Ganak binary not found, installing from sources..."
    git clone git@github.com:meelgroup/ganak.git
    cd ganak
    mkdir build
    cd build
    cmake ..
    make
    ln -s $CWD/ganak $HOME/.local/bin/ganak
    cd ../..
    echo "Ganak installed"
else
    echo "Ganak binary found"
fi

if ! [ -x "$(command -v d4)" ]
then
    echo "d4 (projMC) binary not found, installing from sources..."
    git clone https://github.com/crillab/d4v2
    cd d4v2
    ./build.sh
    ln -s $CWD/build/d4 $HOME/.local/bin/d4
    echo "d4 installed"
    cd ..
else
    echo "d4 binary found"
fi

if ! [ -x "$(command -v schlandals)" ]
then
    echo "Schlandals binary not found, installing from sources..."
    git clone git@github.com:AlexandreDubray/schlandals.git
    cd schlandals
    cargo build --release
    ln -s $CWD/target/release/schlandals $HOME/.local/bin/schlandals
    echo "schlandals installed"
    cd ..
else
    echo "schlandals binary found"
fi

if [ $# -ne 1 ]
then
    printf "You must pass 1 argument, the number of thread that will be used by parallel\n"
    exit 1
fi
nb_thread=$1
nb_repeat=5

timestamp=$(date +%Y_%m_%d_%H_%M_%s)
output_dir=results/$timestamp
mkdir -p $output_dir
# Time format for the time commmand. Real_User_Kernel
export TIMEFORMAT=%R_%U_%S
export par_cmd="parallel --bar -j $nb_thread"
timeout=120
export ganak_cmd="$timeout_cmd ganak -q"
export projMC_cmd="$timeout_cmd d4 -m projMC -i"
export schlandals_cmd="$timeout_cmd schlandals --branching articulation -i"
mkdir $output_dir/ganak
mkdir $output_dir/projMC
mkdir $output_dir/schlandals

# First set of benchmarks, bayesian networks
printf "Benchmarking bayesian networks\n"
printf "\tLaunching pcnf files (ganak, projMC)\n"
# The parallel command is used to run the solvers on each benchmarks. There are multiple ways to provide input to parralel which then applies the given command on each input.
# For instance `parallel echo {} ::: $(seq 10)` will print all the numbers from 1 to 10. {} will be replaced by parallel with the input.
# In our case we want to run the solvers on all instances (.cnf files or .ppidimacs files) a given amount of time (to reduce variances in the run time).
# This is done by giving two inputs to parallel. In that case, it will run the command for each possible pair of the inputs (in our case {2} is the second input, the instance file).
# This achieve the wanted effect: for every instance file, we will run $nb_repeat time the command that run the solver on the instance.
# The command of the solver is run in a new bash shell (bash -c '...') because we use ulimit -t to set the total CPU time allowed to the solver.
# Finally, the results are saved in a .csv file and the output of time (on stderr) can be retrieved in that file (used later to generate the plots/stats)
$par_cmd --results $output_dir/ganak/bn.csv "time (bash -c 'ulimit -t $timeout; $ganak_cmd {2} >> /dev/null')" ::: $(seq $nb_repeat) ::: $(find instances/bayesian_networks/ -type f -name '*.cnf') 
$par_cmd --results $output_dir/projMC/bn.csv "time (bash -c 'ulimit -t $timeout; $projMC_cmd {2} >> /dev/null')" ::: $(seq $nb_repeat) ::: $(find instances/bayesian_networks/ -type f -name '*.cnf')
printf "\tLaunching ppidimacs files (schlandals)\n"
$par_cmd --results $output_dir/schlandals/bn.csv "time (bash -c 'ulimit -t $timeout; $schlandals_cmd {2} >> /dev/null')" ::: $(seq $nb_repeat) ::: $(find instances/bayesian_networks/ -type f -name '*.ppidimacs')

printf "Benchmarking power grid transmission\n"
printf "\tLaunching pcnf files (ganak, projMC)\n"
$par_cmd --results $output_dir/ganak/pg.csv "time (bash -c 'ulimit -t $timeout; $ganak_cmd {2} >> /dev/null')" ::: $(seq $nb_repeat) ::: $(find instances/power_transmission_grid/ -type f -name '*.cnf')
$par_cmd --results $output_dir/projMC/pg.csv "time (bash -c 'ulimit -t $timeout; $projMC_cmd {2} >> /dev/null')" ::: $(seq $nb_repeat) ::: $(find instances/power_transmission_grid/ -type f -name '*.cnf')
printf "\tLaunching ppidimacs files (schlandals)\n"
$par_cmd --results $output_dir/schlandals/pg.csv "time (bash -c 'ulimit -t $timeout; $schlandals_cmd {2} >> /dev/null')" ::: $(seq $nb_repeat) ::: $(find instances/power_transmission_grid/ -type f -name '*.ppidimacs')

git add results/$timestamp
git commit -m "auto commit results $timestamp"
git push
