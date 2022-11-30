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
