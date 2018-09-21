#!/usr/bin/python
# -*- coding: utf-8 -*-


import os
import shutil
from lxml import etree
import random
import argparse
from pypaths import astar
from tqdm import tqdm


class MapGenerator(object):
    def __init__(self,
                 map_file,
                 unit_file,
                 enemy_file,
                 location_file,
                 output_dir,
                 generate_count,
                 min_route_count,
                 max_route_count,
                 min_location_count,
                 max_location_count,
                 min_unit_count,
                 max_unit_count,
                 min_enemy_count,
                 max_enemy_count):
        self.map_file = map_file
        self.unit_file = unit_file
        self.enemy_file = enemy_file
        self.location_file = location_file
        self.output_dir = output_dir
        self.generate_count = generate_count
        self.min_route_count = min_route_count
        self.max_route_count = max_route_count
        self.min_location_count = min_location_count
        self.max_location_count = max_location_count
        self.min_unit_count = min_unit_count
        self.max_unit_count = max_unit_count
        self.min_enemy_count = min_enemy_count
        self.max_enemy_count = max_enemy_count
        self.tile_count = 0
        self.tile_size = 0
        self.tiles = []
        self.enabled_tiles = []
        self.id = 0
        self.paths = []
        self.melee_location_gid = 0
        self.ranged_location_gid = 0
        self.enemies = []
        self.melee_units = []
        self.ranged_units = []
        self.route_elements = []
        self.location_element = None
        self.enemy_elements = []
        self.unit_element = None

    def generate(self, generate_count, output_dir):
        parser = etree.XMLParser(remove_blank_text=True)
        map_data = etree.parse(self.map_file, parser=parser)
        map_element = map_data.xpath('//map')[0]
        self.tile_count = min(int(map_element.attrib['width']), int(map_element.attrib['height']))
        self.tile_size = min(int(map_element.attrib['tilewidth']), int(map_element.attrib['tileheight']))
        self.tiles = []
        for x in range(self.tile_count):
            for y in range(self.tile_count):
                self.tiles.append((x, y))
        tilesets = map_element.xpath('//tileset')
        self.enemies.clear()
        enemy_data = etree.parse(self.enemy_file)
        enemy_tileset = [x for x in tilesets if x.attrib['source'] == 'enemies.tsx'][0]
        enemy_first_gid = int(enemy_tileset.attrib['firstgid'])
        for element in enemy_data.xpath('//tile'):
            enemy_type = element.attrib['type']
            enemy_id = enemy_first_gid + int(element.attrib['id'])
            self.enemies.append((enemy_type, enemy_id))
        unit_data = etree.parse(self.unit_file)
        self.melee_units.clear()
        unit_tileset = [x for x in tilesets if x.attrib['source'] == 'units.tsx'][0]
        unit_first_gid = int(unit_tileset.attrib['firstgid'])
        for element in unit_data.xpath('//tile'):
            unit_id = unit_first_gid + int(element.attrib['id'])
            properties = element.xpath('//tile[@id=\'{}\']/properties/property'.format(unit_id))
            if [x for x in properties if x.attrib['name'] == 'battle_style' and x.attrib['value'] == 'melee']:
                self.melee_units.append(('melee', unit_id))
            else:
                self.ranged_units.append(('ranged', unit_id))
        location_data = etree.parse(self.location_file)
        location_tileset = [x for x in tilesets if x.attrib['source'] == 'locations.tsx'][0]
        location_first_id = int(location_tileset.attrib['firstgid'])
        for element in location_data.xpath('//tile'):
            location_type = element.attrib['type']
            if location_type == 'melee':
                self.melee_location_gid = location_first_id + int(element.attrib['id'])
            else:
                self.ranged_location_gid = location_first_id + int(element.attrib['id'])

        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir)
        os.mkdir(output_dir)

        for i in tqdm(range(generate_count)):
            map_data = etree.parse(self.map_file, parser=parser)
            map_element = map_data.xpath('//map')[0]

            self._generate_routes()
            self._generate_locations()
            self._generate_enemies()
            self._generate_units()

            for element in self.route_elements:
                map_element.append(element)
            map_element.append(self.location_element)
            for element in self.enemy_elements:
                map_element.append(element)
            map_element.append(self.unit_element)
            map_data.write(os.path.join(output_dir, '{0:03d}.tmx'.format(i)),
                           pretty_print=True,
                           xml_declaration=True,
                           encoding='UTF-8')

    def _generate_routes(self):
        self.paths.clear()
        self.route_elements.clear()
        edge_tiles = list(set([x for x in self.tiles if x[0] == 0 or x[0] == self.tile_count - 1 or x[1] == 0]))
        generate_count = random.randint(self.min_route_count, self.max_route_count)
        start_tiles = random.sample(edge_tiles, generate_count)
        tile_pairs = []
        for start_tile in start_tiles:
            end_tile = random.choice([x for x in edge_tiles
                                      if x != start_tile
                                      and x[0] != start_tile[0]
                                      and not (x[1] == 0 and start_tile[1] == 0)
                                      and abs(x[0] - start_tile[0]) > 3
                                      and abs(x[1] - start_tile[1]) > 3])
            tile_pairs.append((start_tile, end_tile))
        for start, end in tile_pairs:
            while True:
                self.enabled_tiles = \
                    [x for x in random.sample(self.tiles, len(self.tiles)) if x == start or x == end or random.uniform(0, 1) > 0.3]

                finder = astar.pathfinder(neighbors=self._neighbors)
                path = finder(start, end)[1]
                if not path:
                    continue
                if start[0] == 0:
                    actual_start = (start[0] - 1, start[1])
                elif start[0] == self.tile_count - 1:
                    actual_start = (start[0] + 1, start[1])
                else:
                    actual_start = (start[0], start[1] - 1)
                path.insert(0, actual_start)
                if end[0] == 0:
                    actual_end = (end[0] - 1, end[1])
                elif end[0] == self.tile_count - 1:
                    actual_end = (end[0] + 1, end[1])
                else:
                    actual_end = (end[0], end[1] - 1)
                path.append(actual_end)
                self.paths.append(path)
                break
        for i, path in enumerate(self.paths):
            group_element = etree.Element('objectgroup')
            group_element.attrib['name'] = 'route{0:02d}'.format(i)
            id_element = etree.Element('property')
            id_element.attrib['name'] = 'id'
            id_element.attrib['value'] = str(i)
            properties_element = etree.Element('properties')
            properties_element.append(id_element)
            group_element.append(properties_element)
            tmp_path = []
            for index, waypoint in enumerate(path):
                if index == 0:
                    tmp_path.append(waypoint)
                elif index >= len(path) - 1:
                    tmp_path.append(waypoint)
                else:
                    c = path[index]
                    p = path[index - 1]
                    n = path[index + 1]
                    if p[0] == c[0] and c[0] == n[0] or p[1] == c[1] and c[1] == n[1]:
                        continue
                    tmp_path.append(waypoint)
            for index, waypoint in enumerate(tmp_path):
                object_element = etree.Element('object')
                object_element.attrib['id'] = str(self.id)
                object_element.attrib['name'] = str(index)
                object_element.attrib['x'] = str(waypoint[0] * self.tile_size + self.tile_size / 2)
                object_element.attrib['y'] = str(waypoint[1] * self.tile_size + self.tile_size / 2)
                index_element = etree.Element('property')
                index_element.attrib['name'] = 'index'
                index_element.attrib['value'] = str(index)
                properties_element = etree.Element('properties')
                properties_element.append(index_element)
                point_element = etree.Element('point')
                object_element.append(properties_element)
                object_element.append(point_element)
                group_element.append(object_element)
                self.id += 1
            self.route_elements.append(group_element)

    def _neighbors(self, current):
        neighbors = []
        for i, j in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
            neighbor = (current[0] + i, current[1] + j)
            if neighbor != current and neighbor in self.enabled_tiles:
                neighbors.append(neighbor)
        return neighbors

    def _generate_locations(self):
        melee_locations = []
        for path in self.paths:
            for waypoint in path[1:-1]:
                melee_locations.append(waypoint)
        ranged_locations = list(set(random.sample(self.tiles, len(self.tiles))) - set(melee_locations))
        group_element = etree.Element('objectgroup')
        group_element.attrib['name'] = 'locations'
        generate_count = max(self.min_location_count, self.max_location_count)
        for i in range(generate_count):
            is_melee = i >= generate_count / 2
            locations = melee_locations if is_melee else ranged_locations
            if not locations:
                continue
            location = random.choice(locations)
            locations.remove(location)
            object_element = etree.Element('object')
            object_element.attrib['id'] = str(self.id)
            object_element.attrib['type'] = 'melee' if is_melee else 'ranged'
            object_element.attrib['gid'] = str(self.melee_location_gid if is_melee else self.ranged_location_gid)
            object_element.attrib['x'] = str(location[0] * self.tile_size + 16)
            object_element.attrib['y'] = str((location[1] + 1) * self.tile_size - 16)
            object_element.attrib['width'] = str(self.tile_size / 2)
            object_element.attrib['height'] = str(self.tile_size / 2)
            group_element.append(object_element)
            self.id += 1
        self.location_element = group_element

    def _generate_enemies(self):
        self.enemy_elements.clear()
        for i in range(len(self.route_elements)):
            group_element = etree.Element('objectgroup')
            group_element.attrib['name'] = 'enemies{}'.format(i)
            route_element = etree.Element('property')
            route_element.attrib['name'] = 'route'
            route_element.attrib['value'] = '{}'.format(i)
            properties_element = etree.Element('properties')
            properties_element.append(route_element)
            group_element.append(properties_element)
            for entry_index in range(0, random.randint(self.min_enemy_count, self.max_enemy_count)):
                enemy = random.choice(self.enemies)
                object_element = etree.Element('object')
                object_element.attrib['id'] = str(self.id)
                object_element.attrib['type'] = enemy[0]
                object_element.attrib['gid'] = str(enemy[1])
                object_element.attrib['x'] = str(-100)
                object_element.attrib['y'] = str(0)
                index_element = etree.Element('property')
                index_element.attrib['name'] = 'entry_index'
                index_element.attrib['value'] = str(entry_index)
                wait_element = etree.Element('property')
                wait_element.attrib['name'] = 'wait'
                wait_element.attrib['value'] = str(random.randint(0, 10))
                properties_element = etree.Element('properties')
                properties_element.append(index_element)
                properties_element.append(wait_element)
                object_element.append(properties_element)
                group_element.append(object_element)
                self.id += 1
            self.enemy_elements.append(group_element)

    def _generate_units(self):
        group_element = etree.Element('objectgroup')
        group_element.attrib['name'] = 'units'
        generate_count = random.randint(self.min_unit_count, self.max_unit_count)
        for i in range(generate_count):
            unit = random.choice(self.melee_units if i >= generate_count / 2 else self.ranged_units)
            object_element = etree.Element('object')
            object_element.attrib['id'] = str(self.id)
            object_element.attrib['type'] = unit[0]
            object_element.attrib['gid'] = str(unit[1])
            object_element.attrib['x'] = str((self.tile_size / 2) * i)
            object_element.attrib['y'] = str(self.tile_size * (self.tile_count + 2))
            object_element.attrib['width'] = str(self.tile_size / 2)
            object_element.attrib['height'] = str(self.tile_size / 2)
            group_element.append(object_element)
            self.id += 1
        self.unit_element = group_element


def _generate(args):
    generator = MapGenerator(map_file=args.map_file,
                             unit_file=args.unit_file,
                             enemy_file=args.enemy_file,
                             location_file=args.location_file,
                             output_dir=args.output_dir,
                             generate_count=args.generate_count,
                             min_route_count=args.min_route,
                             max_route_count=args.max_route,
                             min_location_count=args.min_location,
                             max_location_count=args.max_location,
                             min_unit_count=args.min_unit,
                             max_unit_count=args.max_unit,
                             min_enemy_count=args.min_enemy,
                             max_enemy_count=args.max_enemy)
    generator.generate(generate_count=args.generate_count, output_dir=args.output_dir)


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--map-file', type=str, default='../assets/maps/empty.tmx')
    parser.add_argument('--unit-file', type=str, default='../assets/maps/units.tsx')
    parser.add_argument('--enemy-file', type=str, default='../assets/maps/enemies.tsx')
    parser.add_argument('--location-file', type=str, default='../assets/maps/locations.tsx')
    parser.add_argument('--output-dir', type=str, default='output')
    parser.add_argument('--generate-count', type=int, default=100)
    parser.add_argument('--min-route', type=int, default=1)
    parser.add_argument('--max-route', type=int, default=3)
    parser.add_argument('--min-location', type=int, default=5)
    parser.add_argument('--max-location', type=int, default=8)
    parser.add_argument('--min-unit', type=int, default=5)
    parser.add_argument('--max-unit', type=int, default=12)
    parser.add_argument('--min-enemy', type=int, default=10)
    parser.add_argument('--max-enemy', type=int, default=20)
    return parser.parse_args()


def main():
    args = _parse_args()
    _generate(args)


if __name__ == '__main__':
    main()
