#! /usr/bin/env bash
printf "Benchmarking on bayesian networks"
timestamp=$1
if [ -z $timestamp ]
then
    timestamp=$(date +%Y_%m_%d_%H_%M_%s)
fi
outputdir=results/$timestamp
export TIMEFORMAT=%R

mkdir -p $outputdir/ganak/bn
mkdir -p $outputdir/projMC/bn
mkdir -p $outputdir/schlandals/bn

ganak() {
    outdir=$1
    input=$2
    IFS='/' read -ra tab <<< $2;
    instance=${tab[-2]}_${tab[-1]};
    time (timeout 1s ganak -q $input >> /dev/null) &>> $outdir/ganak/bn/$instance.time
}
export -f ganak 
projMC() {
    outdir=$1
    input=$2
    IFS='/' read -ra tab <<< $2;
    instance=${tab[-2]}_${tab[-1]};
    time (timeout 1s ganak -q $input >> /dev/null) &>> $outdir/ganak/bn/$instance.time
}
export -f projMC
schlandals() {
    outdir=$1
    input=$2
    IFS='/' read -ra tab <<< $2;
    instance=${tab[-2]}_${tab[-1]};
    time (timeout 1s ganak -q $input >> /dev/null) &>> $outdir/ganak/bn/$instance.time
}
export -f schlandals
printf "\tRunning ganak..."
find 'instances/bayesian_networks/pcnf' -type f -name '*.cnf' | parallel ganak $outputdir
printf "\tRunning projMC..."
find 'instances/bayesian_networks/pcnf' -type f -name '*.cnf' | parallel projMC $outputdir
printf "\tRunning schlandals..."
find 'instances/bayesian_networks/pcnf' -type f -name '*.cnf' | parallel schlandals $outputdir
