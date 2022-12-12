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

if [ $# -lt 2 ]
then
    printf "You must pass at least 2 arguments: i) the number of threads used by parallel ii) the name of the solvers to benchmarks\n"
    printf "If a solver is not benchmarked, its last benchmarks will be copied"
    exit 1
fi
run_ganak=false
run_projMC=false
run_schlandals=false

shift
while [ $# -ne 0 ]
do
    if [ $1 == "ganak" ]
    then
        run_ganak=true
    fi
    if [ $1 == "projMC" ]
    then
        run_projMC=true
    fi
    if [ $1 == "schlandals" ]
    then
        run_schlandals=true
    fi
    shift
done

last_bench_dir=$(ls results/ | sort -i -r | head -n 1)

nb_thread=$1
nb_repeat=5

timestamp=$(date +%Y_%m_%d_%H_%M_%s)
output_dir=results/$timestamp
mkdir -p $output_dir

# copying the old benchmarks if any, for the solver not benchmarked
# if no benchmarks present, exit
if [ $run_ganak = false ]
then
    cp -r results/$last_bench_dir/ganak $output_dir/ganak
else
    mkdir $output_dir/ganak
fi
if [ $run_projMC = false ]
then
    cp -r results/$last_bench_dir/projMC $output_dir/projMC
else
    mkdir $output_dir/projMC
fi
if [ $run_schlandals = false ]
then
    cp -r results/$last_bench_dir/schlandals $output_dir/schlandals
else
    mkdir $output_dir/schlandals
fi

# Time format for the time commmand. Real_User_Kernel
export TIMEFORMAT=%R_%U_%S
export par_cmd="parallel --bar -j $nb_thread"
timeout=120
# 5 seconds buffer for correct timeout
buf_timeout=$(($timeout + 5))
export ganak_cmd="$timeout_cmd ganak -q"
export projMC_cmd="$timeout_cmd d4 -m projMC -i"
export schlandals_cmd="$timeout_cmd schlandals --branching articulation -i"

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
if [ $run_ganak = true ]
then
    $par_cmd --results $output_dir/ganak/bn.csv "time (bash -c 'ulimit -t $buf_timeout; $ganak_cmd {2}' &>> /dev/null)" ::: $(seq $nb_repeat) ::: $(find instances/bayesian_networks/ -type f -name '*.cnf') 
fi
if [ $run_projMC = true ]
then
    $par_cmd --results $output_dir/projMC/bn.csv "time (bash -c 'ulimit -t $buf_timeout; $projMC_cmd {2}' &>> /dev/null)" ::: $(seq $nb_repeat) ::: $(find instances/bayesian_networks/ -type f -name '*.cnf')
fi
printf "\tLaunching ppidimacs files (schlandals)\n"
if [ $run_schlandals = true ]
then
    $par_cmd --results $output_dir/schlandals/bn.csv "time (bash -c 'ulimit -t $buf_timeout; $schlandals_cmd {2}' &>> /dev/null)" ::: $(seq $nb_repeat) ::: $(find instances/bayesian_networks/ -type f -name '*.ppidimacs')
fi

printf "Benchmarking power grid transmission\n"
printf "\tLaunching pcnf files (ganak, projMC)\n"
if [ $run_ganak = true ]
then
    $par_cmd --results $output_dir/ganak/pg.csv "time (bash -c 'ulimit -t $buf_timeout; $ganak_cmd {2}' &>> /dev/null)" ::: $(seq $nb_repeat) ::: $(find instances/power_transmission_grid/ -type f -name '*.cnf')
fi
if [ $run_projMC = true ]
then
    $par_cmd --results $output_dir/projMC/pg.csv "time (bash -c 'ulimit -t $buf_timeout; $projMC_cmd {2}' &>> /dev/null)" ::: $(seq $nb_repeat) ::: $(find instances/power_transmission_grid/ -type f -name '*.cnf')
fi
printf "\tLaunching ppidimacs files (schlandals)\n"
if [ $run_schlandals = true ]
then
    $par_cmd --results $output_dir/schlandals/pg.csv "time (bash -c 'ulimit -t $buf_timeout; $schlandals_cmd {2}' &>> /dev/null)" ::: $(seq $nb_repeat) ::: $(find instances/power_transmission_grid/ -type f -name '*.ppidimacs')
fi

mkdir -p $output_dir/plots
plot_readme=$output_dir/plots/README.md

# print the config used in the plot file
# We assume that the solver have been installed from source and are symlinked
ganak_base_dir=$(dirname $(readlink -f $(command -v ganak)))
projMC_base_dir=$(dirname $(readlink -f $(command -v d4)))
schlandals_base_dir=$(dirname $(readlink -f $(command -v schlandals)))
cur_dir=$(pwd)

get_git_hash () {
    cd $1
    if [[ $(git rev-parse --quiet --git-dir) ]]
    then
        hash=$(git rev-parse HEAD)
        if [[ "$hash" == "$2" ]]
        then
            echo "-"
        else
            echo $hash
        fi
    else
        echo "-"
    fi
}

touch $plot_readme
bench_git_hash=$(git rev-parse HEAD)
ganak_hash=$(get_git_hash $ganak_base_dir $bench_git_hash)
projMC_hash=$(get_git_hash $projMC_base_dir $bench_git_hash)
schlandals_hash=$(get_git_hash $schlandals_base_dir $bench_git_hash)
cd $cur_dir

echo \# Solvers configurations >> $plot_readme
echo \#\#\# Ganak >> $plot_readme
echo Commit hash $ganak_hash >> $plot_readme
echo Command $ganak_cmd >> $plot_readme
echo \#\#\# projMC >> $plot_readme
echo Commit hash $projMC_hash >> $plot_readme
echo Command $projMC_cmd >> $plot_readme
echo \#\#\# Schlandals >> $plot_readme
echo Commit hash $schlandals_hash >> $plot_readme
echo Command $schlandals_cmd >> $plot_readme

python3 graphs.py $timestamp $timeout ganak projMC schlandals

git add results/$timestamp
git commit -m "auto commit results $timestamp"
git push
