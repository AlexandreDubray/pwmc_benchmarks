instances=(alarm andes asia barley cancer child diabetes earthquake hailfinder hepar2 insurance mildew munin pathfinder pigs sachs survey water win95pts)
for inst in "${instances[@]}"
do
    ./bn2cnf_linux -i uai/$inst.uai -o enc4_tpl/$inst.cnf -w enc4_tpl/$inst.weights -v enc4_tpl/$inst.map
done