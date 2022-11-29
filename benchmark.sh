#! /usr/bin/env bash

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

timestamp=$(date +%Y_%m_%d_%H_%M_%s)
./bn_benchmarks.sh $timestamp
./pg_benchmarks.sh $timestamp
git add results/$timestamp
git commit -m "auto commit result $timestamp"
git push
