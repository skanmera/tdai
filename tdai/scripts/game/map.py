#!/usr/bin/python
# -*- coding: utf-8 -*-


__author__ = "skanmera"
__copyright__ = "Copyright 2018, skanmera"

from .sprite import Sprite


class Location(Sprite):

    def __init__(self, game, obj):
        super().__init__(game=game, image=obj.image, x=obj.x, y=obj.y)
        self.id = obj.id
        self.type = obj.type
        self.unit = None
        self.x += self.w / 2
        self.y += self.h / 2

    def try_put_unit(self, unit):
        if self.unit:
            return False
        if self.type != unit.battle_style:
            return False
        self.unit = unit
        return True

    def on_unit_withdrawn(self):
        self.unit = None


class Route(object):

    def __init__(self, layer):
        self.id = int(layer.id)
        self.waypoints = list(layer)
        self.waypoints.sort(key=lambda x: int(x.index))

    @property
    def goal(self):
        return self.waypoints[-1]

    def get_next_waypoint(self, current):
        if self.is_terminal_waypoint(current):
            return None
        return self.waypoints[int(current.index) + 1]

    def is_terminal_waypoint(self, waypoint):
        return int(waypoint.index) >= len(self.waypoints) - 1

    def get_start_waypoint(self):
        return self.waypoints[0]
