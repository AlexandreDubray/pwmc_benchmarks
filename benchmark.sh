#! /usr/bin/env bash

function usage {
    echo "Usage: $(basename $0) [ -t N ] [-hGPSbw]" 2>&1
    echo '  -h : shows this help message'
    echo '  -t N : use N threads for the benchmarks'
    echo '  -G : run the ganak solver'
    echo '  -P : run the projMC solver'
    echo '  -S : run the schlandals solver'
    echo '  -b : run the bayesian network benchmarks'
    echo '  -w : run the water supply network benchmarks'
    exit 1
}

if [[ ${#} -eq 0 ]]; then
    usage
fi

run_ganak=false
run_projMC=false
run_schlandals=false

run_bn=false
run_wn=false

optstring=":ht:GPSbw"
while getopts ${optstring} arg; do
    case ${arg} in
        h)
            usage
            ;;
        t)
            nb_thread="${OPTARG}"
            ;;
        G)
            run_ganak=true
            ;;
        P)
            run_projMC=true
            ;;
        S)
            run_schlandals=true
            ;;
        b)
            run_bn=true
            ;;
        w)
            run_wn=true
            ;;
        ?)
            echo "Invalid option: -${OPTARG}."
            echo
            usage
            ;;
    esac
done

if [ $run_ganak = false ] && [ $run_projMC = false ] && [ $run_schlandals = false ]
then
    echo "No solver have been selected to benchmark. Exiting"
    exit 0
fi

# Installs the solvers if not present in the PATH
if [ $run_ganak = true ] && ! [ -x "$(command -v ganak)" ]
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
fi

if [ $run_projMC = true ] && ! [ -x "$(command -v d4)" ]
then
    echo "d4 (projMC) binary not found, installing from sources..."
    git clone https://github.com/crillab/d4v2
    cd d4v2
    ./build.sh
    ln -s $CWD/build/d4 $HOME/.local/bin/d4
    echo "d4 installed"
    cd ..
fi

if [ run_schlandals = true ] && ! [ -x "$(command -v schlandals)" ]
then
    echo "Schlandals binary not found, installing from sources..."
    git clone git@github.com:AlexandreDubray/schlandals.git
    cd schlandals
    cargo build --release
    ln -s $CWD/target/release/schlandals $HOME/.local/bin/schlandals
    echo "schlandals installed"
    cd ..
fi

last_bench_dir=$(ls results/ | sort -i -r | head -n 1)
nb_repeat=5

timestamp=$(date +%Y_%m_%d_%H_%M_%s)
output_dir=results/$timestamp
mkdir -p $output_dir
mkdir -p $output_dir/ganak
mkdir -p $output_dir/projMC
mkdir -p $output_dir/schlandals

# Time format for the time commmand. Real_User_Kernel
export TIMEFORMAT=%R_%U_%S
export par_cmd="parallel --bar -j $nb_thread"
timeout=120
# 5 seconds buffer for correct timeout
buf_timeout=$(($timeout + 5))
export ganak_cmd="$timeout_cmd ganak -q"
export projMC_cmd="$timeout_cmd d4 -m projMC -i"
export schlandals_cmd="$timeout_cmd schlandals -b children-fiedler-avg -i"

# The parallel command is used to run the solvers on each benchmarks. There are multiple ways to provide input to parralel which then applies the given command on each input.
# For instance \`parallel echo {} ::: $(seq 10)\` will print all the numbers from 1 to 10. {} will be replaced by parallel with the input.
# In our case we want to run the solvers on all instances (.cnf files or .ppidimacs files) a given amount of time (to reduce variances in the run time).
# This is done by giving two inputs to parallel. In that case, it will run the command for each possible pair of the inputs (in our case {2} is the second input, the instance file).
# This achieve the wanted effect: for every instance file, we will run $nb_repeat time the command that run the solver on the instance.
# The command of the solver is run in a new bash shell (bash -c '...') because we use ulimit -t to set the total CPU time allowed to the solver.
# Finally, the results are saved in a .csv file and the output of time (on stderr) can be retrieved in that file (used later to generate the plots/stats)
if [ $run_bn = true ]
then
    printf "Benchmarking bayesian networks\n"
    if [ $run_ganak = true ]
    then
        $par_cmd --results $output_dir/ganak/bn.csv "time (bash -c 'ulimit -t $buf_timeout; $ganak_cmd {2}' &>> /dev/null)" ::: $(seq $nb_repeat) ::: $(find instances/bayesian_networks/ -type f -name '*.cnf') 
    else
        cp -r results/$last_bench_dir/ganak/bn.csv $output_dir/ganak/bn.csv
    fi
    if [ $run_projMC = true ]
    then
        $par_cmd --results $output_dir/projMC/bn.csv "time (bash -c 'ulimit -t $buf_timeout; $projMC_cmd {2}' &>> /dev/null)" ::: $(seq $nb_repeat) ::: $(find instances/bayesian_networks/ -type f -name '*.cnf')
    else
        cp -r results/$last_bench_dir/projMC/bn.csv $output_dir/projMC/bn.csv
    fi
    if [ $run_schlandals = true ]
    then
        $par_cmd --results $output_dir/schlandals/bn.csv "time (bash -c 'ulimit -t $buf_timeout; $schlandals_cmd {2}' &>> /dev/null)" ::: $(seq $nb_repeat) ::: $(find instances/bayesian_networks/ -type f -name '*.ppidimacs')
    else
        cp -r results/$last_bench_dir/schlandals/bn.csv $output_dir/schlandals/bn.csv
    fi
else
    cp -r results/$last_bench_dir/ganak/bn.csv $output_dir/ganak/bn.csv
    cp -r results/$last_bench_dir/projMC/bn.csv $output_dir/projMC/bn.csv
    cp -r results/$last_bench_dir/schlandals/bn.csv $output_dir/schlandals/bn.csv
fi

#printf "Benchmarking power grid transmission\n"
#printf "\tLaunching pcnf files (ganak, projMC)\n"
#if [ $run_ganak = true ]
#then
#    $par_cmd --results $output_dir/ganak/pg.csv "time (bash -c 'ulimit -t $buf_timeout; $ganak_cmd {2}' &>> /dev/null)" ::: $(seq $nb_repeat) ::: $(find instances/power_transmission_grid/ -type f -name '*.cnf')
#fi
#if [ $run_projMC = true ]
#then
#    $par_cmd --results $output_dir/projMC/pg.csv "time (bash -c 'ulimit -t $buf_timeout; $projMC_cmd {2}' &>> /dev/null)" ::: $(seq $nb_repeat) ::: $(find instances/power_transmission_grid/ -type f -name '*.cnf')
#fi
#printf "\tLaunching ppidimacs files (schlandals)\n"
#if [ $run_schlandals = true ]
#then
#    $par_cmd --results $output_dir/schlandals/pg.csv "time (bash -c 'ulimit -t $buf_timeout; $schlandals_cmd {2}' &>> /dev/null)" ::: $(seq $nb_repeat) ::: $(find instances/power_transmission_grid/ -type f -name '*.ppidimacs')
#fi

if [ $run_wn = true ]
then
    echo "Running water supply network benchmark"
    if [ $run_ganak = true ]
    then
        $par_cmd --results $output_dir/ganak/wn.csv "time (bash -c 'ulimit -t $buf_timeout; $ganak_cmd {2}' &>> /dev/null)" ::: $(seq $nb_repeat) ::: $(find instances/water-supply-network/ -type f -name '*.cnf') 
    else
        cp -r results/$last_bench_dir/ganak/wn.csv $output_dir/ganak/wn.csv
    fi
    if [ $run_projMC = true ]
    then
        $par_cmd --results $output_dir/projMC/wn.csv "time (bash -c 'ulimit -t $buf_timeout; $projMC_cmd {2}' &>> /dev/null)" ::: $(seq $nb_repeat) ::: $(find instances/water-supply-network/ -type f -name '*.cnf')
    else
        cp -r results/$last_bench_dir/projMC/wn.csv $output_dir/projMC/wn.csv
    fi
    if [ $run_schlandals = true ]
    then
        $par_cmd --results $output_dir/schlandals/wn.csv "time (bash -c 'ulimit -t $buf_timeout; $schlandals_cmd {2}' &>> /dev/null)" ::: $(seq $nb_repeat) ::: $(find instances/water-supply-network/ -type f -name '*.ppidimacs')
    else
        cp -r results/$last_bench_dir/schlandals/wn.csv $output_dir/schlandals/wn.csv
    fi
else
    cp -r results/$last_bench_dir/ganak/wn.csv $output_dir/ganak/wn.csv
    cp -r results/$last_bench_dir/projMC/wn.csv $output_dir/projMC/wn.csv
    cp -r results/$last_bench_dir/schlandals/wn.csv $output_dir/schlandals/wn.csv
fi


plot_readme=$output_dir/README.md

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

printf "%s\n" "\# Solvers configurations" >> $plot_readme
printf "%s\n" "\#\#\# Ganak" >> $plot_readme
printf "%s\n" "- Commit hash: $ganak_hash" >> $plot_readme
printf "%s\n" "- Command: \`$ganak_cmd\`\n" >> $plot_readme
printf "%s\n" "\#\#\# projMC" >> $plot_readme
printf "%s\n" "- Commit hash: $projMC_hash" >> $plot_readme
printf "%s\n" "- Command: \`$projMC_cmd\`\n" >> $plot_readme
printf "%s\n" "\#\#\# Schlandals" >> $plot_readme
printf "%s\n" "- Commit hash: $schlandals_hash" >> $plot_readme
printf "%s\n" "- Command: \`$schlandals_cmd\`\n" >> $plot_readme

python3 graphs.py $timestamp $last_bench_dir $timeout ganak projMC schlandals

git add results/$timestamp
git commit -m "auto commit results $timestamp"
git push
