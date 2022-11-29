#! /usr/bin/env bash
printf "Benchmarking on bayesian networks\n"
timestamp=$1
if [ -z $timestamp ]
then
    timestamp=$(date +%Y_%m_%d_%H_%M_%s)
fi
outputdir=results/$timestamp
export TIMEFORMAT=%R
par_cmd="parallel --bar -j 10"
export timeout_cmd="timeout 120s"

mkdir -p $outputdir/ganak/bn
mkdir -p $outputdir/projMC/bn
mkdir -p $outputdir/schlandals/bn

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

printf "\tBenchmarking on pcnf files...\n"
find instances/bayesian_networks/pcnf -type d | while read directory
do
    IFS='/' read -ra instance_name <<< $directory;
    printf "\t\tRunning ganak on instance ${instance_name[-1]}\n"
    find $directory -type f -name '*.cnf' | $par_cmd ganak {} $outputdir/ganak/bn/${instance_name[-1]}_{/.}.time $timeout
    printf "\t\tRunning projMC on instance ${instance_name[-1]}\n"
    find $directory -type f -name '*.cnf' | $par_cmd projMC {} $outputdir/projMC/bn/${instance_name[-1]}_{/.}.time $timeout
done
printf "\tBenchmarking on ppidimacs files...\n"
find instances/bayesian_networks/ppidimacs -type d | while read directory
do
    IFS='/' read -ra instance_name <<< $directory;
    printf "\t\tRunning Schlandals on instance ${instance_name[-1]}\n"
    find $directory -type f -name '*.ppidimacs' | $par_cmd schlandals {} $outputdir/schlandals/bn/${instance_name[1]}_{/.}.time $timeout
done
