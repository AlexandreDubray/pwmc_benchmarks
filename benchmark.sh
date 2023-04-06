#! /usr/bin/env bash

function usage {
    echo "Usage: $(basename $0) [ -t N ] [-hGPSbw]" 2>&1
    echo '  -h : shows this help message'
    echo '  -Y : run the sYm ganak solver'
    echo '  -P : run the projMC solver'
    echo '  -S : run the schlandals solver'
    echo '  -D : run the DPMC solver'
    echo '  -G : run the GPMC solver'
    echo '  -b : run the bayesian network benchmarks'
    echo '  -w : run the water supply network benchmarks'
    echo '  -p : run the power grid network benchmarks'
    exit 1
}

if [[ ${#} -eq 0 ]]; then
    usage
fi

run_projMC=false
run_schlandals=false
run_symganak=false
run_dpmc=false
run_gpmc=false
solver_selected=false

run_bn=false
run_wn=false
run_pg=false

optstring=":ht:GPSYbwp"
while getopts ${optstring} arg; do
    case ${arg} in
        h)
            usage
            ;;
	Y)
	    run_symganak=true
	    solver_selected=true
	    ;;
        P)
            run_projMC=true
	    solver_selected=true
            ;;
        S)
            run_schlandals=true
	    solver_selected=true
            ;;
	D)
	    run_dpmc=true
	    solver_selected=true
	    ;;
	G)
	    run_gpmc=true
	    solver_selected=true
	    ;;
        b)
            run_bn=true
            ;;
        w)
            run_wn=true
            ;;
	p)
	   run_pg=true
	   ;;
        ?)
            echo "Invalid option: -${OPTARG}."
            echo
            usage
            ;;
    esac
done

if [ $solver_selected = false ]
then
    echo "No solver have been selected to benchmark. Exiting"
    exit 1
fi

if [ $run_symganak = true ] && ! [ -x "$(command -v ganak)" ]
then
   echo "Ganak binary not found, exiting."
   exit 1
fi

if [ $run_projMC = true ] && ! [ -x "$(command -v d4)" ]
then
    echo "d4 (projMC) binary not found, exiting."
    exit 1
fi

if [ $run_schlandals = true ] && ! [ -x "$(command -v schlandals)" ]
then
    echo "Schlandals binary not found, exiting."
    exit 1
fi

if [ $run_dpmc = true ] && ! [ -x "$(command -v dpmc)" ] && ! [ -x "$(command -v htb)" ]
then
   echo "DPMC binaries (dpmc / htb) not found, exiting."
   exit 1
fi

if [ $run_gpmc = true ] && ! [ -x  "$(command -v gpmc)"  ] && ! [ -x "$(command -v gpmc)" ]
then
   echo "GPMC binary not found, exiting."
   exit 1
fi

last_bench_dir=$(ls results/ | sort -i -r | head -n 1)
nb_repeat=1

timestamp=$(date +%Y_%m_%d_%H_%M_%s)
output_dir=results/$timestamp
mkdir -p $output_dir
mkdir -p $output_dir/symganak
mkdir -p $output_dir/projMC
mkdir -p $output_dir/schlandals
mkdir -p $output_dir/dpmc
mkdir -p $output_dir/gpmc

# Time format for the time commmand. Real_User_Kernel
export TIMEFORMAT=%R_%U_%S
export par_cmd="parallel --bar "
timeout=600
# 5 seconds buffer for correct timeout
buf_timeout=$(($timeout + 5))
export symganak_cmd="symganak -cs 15000 -q {}"
export projMC_cmd="d4 -m projMC -f 1 -i {}"
export schlandals_cmd="schlandals -b fiedler -m 15000 -i {}"
export dpmc_cmd="htb --cf {} --pc 1 | dmc --cf {} --pc 1"
export gpmc_cmd="gpmc {} -mode=3 -mem-lim=15000"


# The parallel command is used to run the solvers on each benchmarks. There are multiple ways to provide input to parralel which then applies the given command on each input.
# For instance \`parallel echo {} ::: $(seq 10)\` will print all the numbers from 1 to 10. {} will be replaced by parallel with the input.
# In our case we want to run the solvers on all instances (.cnf files or .ppidimacs files) a given amount of time (to reduce variances in the run time).
# This is done by giving two inputs to parallel. In that case, it will run the command for each possible pair of the inputs (in our case {2} is the second input, the instance file).
# This achieve the wanted effect: for every instance file, we will run $nb_repeat time the command that run the solver on the instance.
# The command of the solver is run in a new bash shell (bash -c '...') because we use ulimit -t to set the total CPU time allowed to the solver.
# Finally, the results are saved in a .csv file and the output of time (on stderr) can be retrieved in that file (used later to generate the plots/stats)
# $1 = run or not the solver
# $2 = nb threads
# $3 = output file
# $4 = cmd to run
# $5 = input directory
# $6 = file type
function run_or_copy() {
   if [ $1 = true ]
   then
	   echo $2
	   $par_cmd -j $2 --result $output_dir/$3 "time (bash -c 'ulimit -t $buf_timeout; $4 {}' &>> /dev/null)" ::: $(find $5 -type f -name $6)
   else
	   cp results/$last_bench_dir/$3 $output_dir/$3
   fi
}

if [ $run_bn = true ]
then
    input_dir="instances/bayesian_networks/"
    nbthread=20
    run_or_copy $run_symganak $nbthread "symganak/bn.csv" "$symganak_cmd" $input_dir "*.cnf"
    run_or_copy $run_projMC $nbthread "projMC/bn.csv" "$projMC_cmd" $input_dir "*.cnf"
    run_or_copy $run_dpmc $nbthread "dpmc/bn.csv" "$dpmc_cmd" $input_dir "*.cnf"
    run_or_copy $run_gpmc $nbthread "gpmc/bn.csv" "$gpmc_cmd" $input_dir "*.cnf"
    run_or_copy $run_schlandals $nbthread "schlandals/bn.csv" "$schlandals_cmd" $input_dir "*.ppidimacs"
    # Running the instances with preprocessed PLE
    run_or_copy $run_symganak $nbthread "symganak/bn_ple.csv" "$symganak_cmd" $input_dir "*.cnf.ple"
    run_or_copy $run_projMC $nbthread "projMC/bn_ple.csv" "$projMC_cmd" $input_dir "*.cnf.ple"
    run_or_copy $run_dpmc $nbthread "dpmc/bn_ple.csv" "$dpmc_cmd" $input_dir "*.cnf.ple"
    run_or_copy $run_gpmc $nbthread "gpmc/bn_ple.csv" "$gpmc_cmd" $input_dir "*.cnf.ple"
else
    cp -r results/$last_bench_dir/symganak/bn.csv $output_dir/symganak/bn.csv
    cp -r results/$last_bench_dir/projMC/bn.csv $output_dir/projMC/bn.csv
    cp -r results/$last_bench_dir/schlandals/bn.csv $output_dir/schlandals/bn.csv
    cp -r results/$last_bench_dir/dpmc/bn.csv $output_dir/dpmc/bn.csv
    cp -r results/$last_bench_dir/gpmc/bn.csv $output_dir/gpmd/bn.csv
fi

if [ $run_pg = true ]
then
    nbthread=80
    input_dir="instances/power_transmission_grid/"
    run_or_copy $run_symganak $nbthread "symganak/pg.csv" "$symganak_cmd" $input_dir "*.cnf"
    run_or_copy $run_projMC $nbthread "projMC/pg.csv" "$projMC_cmd" $input_dir "*.cnf"
    run_or_copy $run_dpmc $nbthread "dpmc/pg.csv" "$dpmc_cmd" $input_dir "*.cnf"
    run_or_copy $run_gpmc $nbthread "gpmc/pg.csv" "$gpmc_cmd" $input_dir "*.cnf"
    run_or_copy $run_schlandals $nbthread "schlandals/pg.csv" "$schlandals_cmd" $input_dir "*.ppidimacs"
    # Running the instances with preprocessed PLE
    run_or_copy $run_symganak $nbthread "symganak/pg_ple.csv" "$symganak_cmd" $input_dir "*.cnf.ple"
    run_or_copy $run_projMC $nbthread "projMC/pg_ple.csv" "$projMC_cmd" $input_dir "*.cnf.ple"
    run_or_copy $run_dpmc $nbthread "dpmc/pg_ple.csv" "$dpmc_cmd" $input_dir "*.cnf.ple"
    run_or_copy $run_gpmc $nbthread "gpmc/pg_ple.csv" "$gpmc_cmd" $input_dir "*.cnf.ple"
else
    cp -r results/$last_bench_dir/symganak/pg.csv $output_dir/symganak/pg.csv
    cp -r results/$last_bench_dir/projMC/pg.csv $output_dir/projMC/pg.csv
    cp -r results/$last_bench_dir/schlandals/pg.csv $output_dir/schlandals/pg.csv
    cp -r results/$last_bench_dir/dpmc/pg.csv $output_dir/dpmc/pg.csv
    cp -r results/$last_bench_dir/gpmc/pg.csv $output_dir/gpmd/pg.csv
fi

if [ $run_wn = true ]
then
    echo "Running water supply network benchmark"
    nbthread=80
    input_dir="instances/water-supply-network/"
    run_or_copy $run_symganak $nbthread "symganak/wn.csv" "$symganak_cmd" $input_dir "*.cnf"
    run_or_copy $run_projMC $nbthread "projMC/wn.csv" "$projMC_cmd" $input_dir "*.cnf"
    run_or_copy $run_dpmc $nbthread "dpmc/wn.csv" "$dpmc_cmd" $input_dir "*.cnf"
    run_or_copy $run_gpmc $nbthread "gpmc/wn.csv" "$gpmc_cmd" $input_dir "*.cnf"
    run_or_copy $run_schlandals $nbthread "schlandals/wn.csv" "$schlandals_cmd" $input_dir "*.ppidimacs"
    # Running the instances with preprocessed PLE
    run_or_copy $run_symganak $nbthread "symganak/wn_ple.csv" "$symganak_cmd" $input_dir "*.cnf.ple"
    run_or_copy $run_projMC $nbthread "projMC/wn_ple.csv" "$projMC_cmd" $input_dir "*.cnf.ple"
    run_or_copy $run_dpmc $nbthread "dpmc/wn_ple.csv" "$dpmc_cmd" $input_dir "*.cnf.ple"
    run_or_copy $run_gpmc $nbthread "gpmc/wn_ple.csv" "$gpmc_cmd" $input_dir "*.cnf.ple"
else
    cp -r results/$last_bench_dir/symganak/wn_ple.csv $output_dir/symganak/wn_ple.csv
    cp -r results/$last_bench_dir/projMC/wn_ple.csv $output_dir/projMC/wn_ple.csv
    cp -r results/$last_bench_dir/dpmc/wn_ple.csv $output_dir/dpmc/wn_ple.csv
    cp -r results/$last_bench_dir/gpmc/wn_ple.csv $output_dir/gpmd/wn_ple.csv

    cp -r results/$last_bench_dir/symganak/wn_ple.csv $output_dir/symganak/wn_ple.csv
    cp -r results/$last_bench_dir/projMC/wn_ple.csv $output_dir/projMC/wn_ple.csv
    cp -r results/$last_bench_dir/dpmc/wn_ple.csv $output_dir/dpmc/wn_ple.csv
    cp -r results/$last_bench_dir/gpmc/wn_ple.csv $output_dir/gpmd/wn_ple.csv

    cp -r results/$last_bench_dir/schlandals/wn.csv $output_dir/schlandals/wn.csv
fi

plot_readme=$output_dir/README.md

# print the config used in the plot file
# We assume that the solver have been installed from source and are symlinked
ganak_base_dir=$(dirname $(readlink -f $(command -v symganak)))
projMC_base_dir=$(dirname $(readlink -f $(command -v d4)))
schlandals_base_dir=$(dirname $(readlink -f $(command -v schlandals)))
dpmc_base_dir=$(dirname $(readlink -f $(command -v dmc)))
gpmc_base_dir=$(dirname $(readlink -f $(command -v gpmc)))
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
symganak_hash=$(get_git_hash $symganak_base_bir $bench_git_hash)
projMC_hash=$(get_git_hash $projMC_base_dir $bench_git_hash)
dpmc_hash=$(get_git_hash $dpmc_base_dir $bench_git_hash)
gpmc_hash=$(get_git_hash $gpmc_base_dir $bench_git_hash)
schlandals_hash=$(get_git_hash $schlandals_base_dir $bench_git_hash)
cd $cur_dir

printf "%s\n\n" "\# Solvers configurations" >> $plot_readme
printf "%s\n" "\#\#\# Ganak" >> $plot_readme
printf "%s\n" "- Commit hash: $symganak_hash" >> $plot_readme
printf "%s\n\n" "- Command: \`$symganak_cmd\`" >> $plot_readme

printf "%s\n" "\#\#\# projMC" >> $plot_readme
printf "%s\n" "- Commit hash: $projMC_hash" >> $plot_readme
printf "%s\n\n" "- Command: \`$projMC_cmd\`" >> $plot_readme

printf "%s\n" "\#\#\# DPMC" >> $plot_readme
printf "%s\n" "- Commit hash: $dpmc_hash" >> $plot_readme
printf "%s\n\n" "- Command: \`$dpmc_cmd\`" >> $plot_readme

printf "%s\n" "\#\#\# GPMC" >> $plot_readme
printf "%s\n" "- Commit hash: $gpmc_hash" >> $plot_readme
printf "%s\n\n" "- Command: \`$gpmc_cmd\`" >> $plot_readme

printf "%s\n" "\#\#\# Schlandals" >> $plot_readme
printf "%s\n" "- Commit hash: $schlandals_hash" >> $plot_readme
printf "%s\n\n" "- Command: \`$schlandals_cmd\`" >> $plot_readme

python3 graphs.py $timestamp $last_bench_dir $timeout projMC schlandals gpmc

git add results/$timestamp
git commit -m "auto commit results $timestamp"
git push
