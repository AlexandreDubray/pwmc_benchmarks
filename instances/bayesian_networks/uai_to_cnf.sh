instances=(alarm andes asia barley cancer child diabetes earthquake hailfinder hepar2 insurance mildew munin pathfinder pigs sachs survey water win95pts)
mkdir enc4_tpl
mkdir enc4_log_tpl
mkdir enc3_tpl
for inst in "${instances[@]}"
do
    ./bn2cnf_linux -i uai/$inst.uai -o enc3_tpl/$inst.cnf -w enc3_tpl/$inst.weights -v enc3_tpl/$inst.map
    ./bn2cnf_linux -i uai/$inst.uai -o enc4_tpl/$inst.cnf -w enc4_tpl/$inst.weights -v enc4_tpl/$inst.map -s prime
    ./bn2cnf_linux -i uai/$inst.uai -o enc4_log_tpl/$inst.cnf -w enc4_log_tpl/$inst.weights -v enc4_log_tpl/$inst.map -s prime -e LOG
done
