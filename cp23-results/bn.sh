#! /usr/bin/env bash

# Time format for the time commmand. Real_User_Kernel
export TIMEFORMAT=%R_%U_%S
export par_cmd="parallel --bar "
timeout=600
# 5 seconds buffer for correct timeout
buf_timeout=$(($timeout + 5))
export schlandals_cmd_min_in="schlandals -b min-in-degree -m 15000 -i "
export schlandals_cmd_min_out="schlandals -b min-out-degree -m 15000 -i "
export schlandals_cmd_fiedler="schlandals -b fiedler -m 15000 -i "
export schlandals_cmd_max_degree="schlandals -b max-degree -m 15000 -i "

export projMC_cmd="d4 -m projMC -f 1 -i "
export d4_cmd="d4 -m counting -f 1 -i "
export gpmc_cmd="gpmc -mode=3 -cs=15000 "
export gpmc_cmd_counting="gpmc -mode=1 -cs=15000 "


# The parallel command is used to run the solvers on each benchmarks. There are multiple ways to provide input to parralel which then applies the given command on each input.
# For instance \`parallel echo {} ::: $(seq 10)\` will print all the numbers from 1 to 10. {} will be replaced by parallel with the input.
# In our case we want to run the solvers on all instances (.cnf files or .ppidimacs files) a given amount of time (to reduce variances in the run time).
# This is done by giving two inputs to parallel. In that case, it will run the command for each possible pair of the inputs (in our case {2} is the second input, the instance file).
# This achieve the wanted effect: for every instance file, we will run the command that run the solver on the instance.
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
	   $par_cmd -j $2 --result $output_dir/$3 "time (bash -c 'ulimit -t $buf_timeout; $4 {}' &>> /dev/null)" ::: $(find $5 -type f -name $6)
   else
	   cp results/$last_bench_dir/$3 $output_dir/$3
   fi
}
output_dir="."

nbthread=50
input_dir="../instances/bayesian_networks/ppidimacs"
#run_or_copy true $nbthread "bn/bn_min_in.csv" "$schlandals_cmd_min_in" $input_dir "*.ppidimacs"

input_dir="../instances/bayesian_networks/enc1"
#run_or_copy true $nbthread "bn/d4_enc1.csv" "$d4_cmd" $input_dir "*.cnf"
nbthread=40
#run_or_copy true $nbthread "bn/gpmc_enc1.csv" "$gpmc_cmd_counting" $input_dir "*.cnf"

nbthread=50
input_dir="../instances/bayesian_networks/enc3"
#run_or_copy true $nbthread "bn/d4_enc3.csv" "$d4_cmd" $input_dir "*.cnf"
nbthread=40
#run_or_copy true $nbthread "bn/gpmc_enc3.csv" "$gpmc_cmd_counting" $input_dir "*.cnf"

nbthread=50
input_dir="../instances/bayesian_networks/enc4"
#run_or_copy true $nbthread "bn/d4_enc4.csv" "$d4_cmd" $input_dir "*.cnf"
nbthread=40
#run_or_copy true $nbthread "bn/gpmc_enc4.csv" "$gpmc_cmd_counting" $input_dir "*.cnf"

nbthread=50
input_dir="../instances/bayesian_networks/enc4_log"
#run_or_copy true $nbthread "bn/d4_enc4_log.csv" "$d4_cmd" $input_dir "*.cnf"
nbthread=40
#run_or_copy true $nbthread "bn/gpmc_enc4_log.csv" "$gpmc_cmd_counting" $input_dir "*.cnf"

input_dir="../instances/bayesian_networks/ppidimacs"
nbthread=20
run_or_copy true $nbthread "bn/bn_min_out.csv" "$schlandals_cmd_min_out" $input_dir "*.ppidimacs"

run_or_copy true $nbthread "bn/bn_max_deg.csv" "$schlandals_cmd_max_degree" $input_dir "*.ppidimacs"
run_or_copy true $nbthread "bn/bn_fiedler.csv" "$schlandals_cmd_fiedler" $input_dir "*.ppidimacs"

input_dir="../instances/bayesian_networks/pcnf"
nbthread=50
#run_or_copy true $nbthread "bn/projMC_pcnf.csv" "$projMC_cmd" $input_dir "*.cnf"
nbthread=40
#run_or_copy true $nbthread "bn/gpmc_pcnf.csv" "$gpmc_cmd" $input_dir "*.cnf"

