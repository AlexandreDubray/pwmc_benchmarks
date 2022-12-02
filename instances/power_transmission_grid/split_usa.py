from shapely.geometry import shape, Point
import fiona
import os

_script_dir = os.path.dirname(os.path.realpath(__file__))

print('[power grid] Splitting the USA data set per state...')

na_dir = os.path.join(_script_dir, 'north_america')

states = list(fiona.open(os.path.join(_script_dir, 'usa_borders', 'cb_2016_us_state_500k.shp')))
for i in range(len(states)):
    states[i]['geometry'] = shape(states[i]['geometry'])

map_node_state = {}
vertices_line_state = {state['properties']['NAME']: list() for state in states}
vertices_header = None
links_line_state = {state['properties']['NAME']: list() for state in states}
links_header = None
print('[power grid] Retrieving nodes') 
with open(os.path.join(na_dir, 'gridkit_north_america-highvoltage-vertices.csv')) as f:
    first = True
    for line in f:
        if first:
            vertices_header = line
            first = False
            continue
        s = line.split(',')
        node_id = int(s[0])
        lon = float(s[1])
        lat = float(s[2])
        loc = Point(lon, lat)
        state_name = None
        for state in states:
            if state['geometry'].contains(loc):
                state_name = state['properties']['NAME']
                break
        if state_name is not None:
            map_node_state[node_id] = state_name
            vertices_line_state[state_name].append(line)

print('[power grid] Retrieving edges') 
with open(os.path.join(na_dir, 'gridkit_north_america-highvoltage-links.csv')) as f:
    first = True
    for line in f:
        if first:
            first = False
            links_header = line
            continue
        s = line.split(',')
        n1 = int(s[1])
        state1 = map_node_state[n1] if n1 in map_node_state else None
        n2 = int(s[2])
        state2 = map_node_state[n2] if n2 in map_node_state else None
        if state1 is not None and state1 == state2:
            links_line_state[state1].append(line)

print('[power grid] Writing the data set per state...') 
for state in states:
    name = state['properties']['NAME']
    if len(vertices_line_state[name]) > 0 and len(links_line_state[name]) > 0:
        print(f'\t\t{name}')
        safe_name = name.replace(' ', '_')
        os.makedirs(os.path.join(na_dir, name), exist_ok=True)
        with open(os.path.join(na_dir, safe_name, f'gridkit_{safe_name}-highvoltage-vertices.csv'), 'w') as f:
            f.write(vertices_header)
            for line in vertices_line_state[name]:
                f.write(line)

        with open(os.path.join(na_dir, safe_name, f'gridkit_{safe_name}-highvoltage-links.csv'), 'w') as f:
            f.write(links_header)
            for line in links_line_state[name]:
                f.write(line)
        
