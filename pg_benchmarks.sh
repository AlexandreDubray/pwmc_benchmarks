#! /usr/bin/env bash
printf "Benchmarking on power grid transmission\n"
timestamp=$1
if [ -z $timestamp ]
then
    timestamp=$(date +%Y_%m_%d_%H_%M_%s)
fi
outputdir=results/$timestamp
export TIMEFORMAT=%R
par_cmd="parallel --bar -j 10"
export timeout_cmd="timeout 120s"

mkdir -p $outputdir/ganak/pg
mkdir -p $outputdir/projMC/pg
mkdir -p $outputdir/schlandals/pg

ganak() {
    input=$1
    outputfile=$2
    time ($timeout_cmd ganak -q $input >> /dev/null) &>> $outputfile
}
export -f ganak 

projMC() {
    input=$1
    outputfile=$2
    time ($timeout_cmd d4 -m projMC -i $input >> /dev/null) &>> $outputfile
}
export -f projMC
schlandals() {
    input=$1
    outputfile=$2
    time ($timeout_cmd schlandals --branching articulation -i $input >> /dev/null) &>> $outputfile
}
export -f schlandals

for region in europe north_america
do
    printf "Benchmarking on $region data...\n"
    printf "\tBenchmarking on pcnf files...\n"
    find instances/power_transmission_grid/$region -mindepth 1 -type d | while read directory
    do
        IFS='/' read -ra instance_name <<< $directory;
        printf "\t\tRunning ganak on instance ${instance_name[-1]}\n"
        find $directory/pcnf -type f -name '*.cnf' | $par_cmd ganak {} $outputdir/ganak/pg/${instance_name[-1]}_{/.}.time
        printf "\t\tRunning projMC on instance ${instance_name[-1]}\n"
        find $directory/pcnf -type f -name '*.cnf' | $par_cmd projMC {} $outputdir/projMC/pg/${instance_name[-1]}_{/.}.time
    done
    printf "\tBenchmarking on ppidimacs files...\n"
    find instances/power_transmission_grid/$region -mindepth 1 -type d | while read directory
    do
        IFS='/' read -ra instance_name <<< $directory;
        printf "\t\tRunning Schlandals on instance ${instance_name[-1]}\n"
        find $directory/pcnf -type f -name '*.ppidimacs' | $par_cmd schlandals {} $outputdir/schlandals/bn/${instance_name[1]}_{/.}.time
    done
done
