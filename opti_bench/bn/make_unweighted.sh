mkdir -p uw
for dataset in $(ls enc4)
do
	echo $dataset
	mkdir -p uw/$dataset
	for file in $(ls enc4/$dataset)
	do
		sed -e 's/c p weight/w/g' enc4/$dataset/$file > tmp.cnf
		../../weighted-to-unweighted/weighted_to_unweighted.py --prec 20 tmp.cnf uw/$dataset/$file > uw/${dataset}.div
	done
done
