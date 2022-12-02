from shapely.geometry import shape, Point
import fiona
import os

_script_dir = os.path.dirname(os.path.realpath(__file__))

print('[power grid] Splitting the europe data set per country...')

europe_dir = os.path.join(_script_dir, 'europe')

countries = list(fiona.open(os.path.join(_script_dir, 'world_borders', 'world-borders.shp')))
for i in range(len(countries)):
    countries[i]['geometry'] = shape(countries[i]['geometry'])

map_node_country = {}
vertices_line_country = {country['properties']['NAME']: list() for country in countries}
vertices_header = None
links_line_country = {country['properties']['NAME']: list() for country in countries}
links_header = None
print('[power grid] Retrieving nodes') 
with open(os.path.join(europe_dir, 'gridkit_europe-highvoltage-vertices.csv')) as f:
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
        country_name = None
        for country in countries:
            if country['geometry'].contains(loc):
                country_name = country['properties']['NAME']
                break
        if country_name is not None:
            map_node_country[node_id] = country_name
            vertices_line_country[country_name].append(line)

print('[power grid] Retrieving edges') 
with open(os.path.join(europe_dir, 'gridkit_europe-highvoltage-links.csv')) as f:
    first = True
    for line in f:
        if first:
            first = False
            links_header = line
            continue
        s = line.split(',')
        n1 = int(s[1])
        country1 = map_node_country[n1] if n1 in map_node_country else None
        n2 = int(s[2])
        country2 = map_node_country[n2] if n2 in map_node_country else None
        if country1 is not None and country1 == country2:
            links_line_country[country1].append(line)

print('[power grid] Writing the data set per country...') 
for country in countries:
    name = country['properties']['NAME']
    if len(vertices_line_country[name]) > 0 and len(links_line_country[name]) > 0:
        print(f'\t\t{name}')
        safe_name = name.replace(' ', '_')
        os.makedirs(os.path.join(europe_dir, safe_name), exist_ok=True)
        with open(os.path.join(europe_dir, safe_name, f'gridkit_{safe_name}-highvoltage-vertices.csv'), 'w') as f:
            f.write(vertices_header)
            for line in vertices_line_country[name]:
                f.write(line)

        with open(os.path.join(europe_dir, safe_name, f'gridkit_{safe_name}-highvoltage-links.csv'), 'w') as f:
            f.write(links_header)
            for line in links_line_country[name]:
                f.write(line)
        
