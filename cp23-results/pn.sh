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
export gpmc_cmd="gpmc -mode=3 -cs=15000 "

# $1 = nb threads
# $2 = output file
# $3 = cmd to run
# $4 = input directory
# $5 = file type
function run() {
	$par_cmd -j $1 --result $output_dir/$2 "time (bash -c 'ulimit -t $buf_timeout; $3 {}' &>> /dev/null)" ::: $(find $4 -type f -name $5)
}
output_dir="."
nbthread=50
input_dir="../instances/power_transmission_grid/"
#run $nbthread "pg/pg_min_in.csv" "$schlandals_cmd_min_in" $input_dir "*.ppidimacs"
#run $nbthread "pg/pg_min_out.csv" "$schlandals_cmd_min_out" $input_dir "*.ppidimacs"

run $nbhtread "pg/projMC.csv" "$projMC_cmd" $input_dir "*.pcnf"
nb_thread=20
run $nbhtread "pg/gpmc.csv" "$gpmc_cmd" $input_dir "*.pcnf"

run $nbthread "pg/pg_max_deg.csv" "$schlandals_cmd_max_degree" $input_dir "*.ppidimacs"
run $nbthread "pg/pg_min_fiedler.csv" "$schlandals_cmd_fiedler" $input_dir "*.ppidimacs"

nbthread=50
input_dir="../instances/water-supply-network/"
run $nbthread "wn/wn_min_in.csv" "$schlandals_cmd_min_in" $input_dir "*.ppidimacs"
run $nbthread "wn/wn_min_out.csv" "$schlandals_cmd_min_out" $input_dir "*.ppidimacs"

nbthread=20
run $nbthread "wn/wn_min_fiedler.csv" "$schlandals_cmd_fiedler" $input_dir "*.ppidimacs"
run $nbthread "wn/wn_max_deg.csv" "$schlandals_cmd_max_degree" $input_dir "*.ppidimacs"
