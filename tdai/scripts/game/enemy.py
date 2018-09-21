# -*- coding: utf-8 -*-


__author__ = "skanmera"
__copyright__ = "Copyright 2018, skanmera"


import random
from .battle_object import BattleObject
from ..common.utils import MathUtil as mu


class Enemy(BattleObject):

    def __init__(self, game, route, tmx_obj):
        super().__init__(game=game, tmx_obj=tmx_obj)
        self.route = route
        self.entry_index = int(tmx_obj.entry_index)
        self.trigger_enemy_id = int(tmx_obj.trigger_enemy_id) if hasattr(tmx_obj, 'trigger_enemy_id') else None
        self.trigger_type = tmx_obj.trigger_type if hasattr(tmx_obj, 'trigger_type') else None
        self.speed = float(tmx_obj.speed)
        self.wait = float(tmx_obj.wait) * self.game.fps
        self.current_waypoint = route.get_start_waypoint()
        self.x, self.y = self.current_waypoint.x, self.current_waypoint.y
        self.next_waypoint = route.get_next_waypoint(self.current_waypoint)
        # Prevent completely overlap of enemies.
        self.next_pos = self.next_waypoint.x + random.randint(-10, 10), self.next_waypoint.y + random.randint(-10, 10)
        self.entered = False
        self.blocked_unit = None

    def _enter(self):
        if not self.entered:
            if self.trigger_enemy_id:
                trigger_enemy = self.game.enemies.first(lambda x: x.id == self.trigger_enemy_id)
                if self.trigger_type == 'entered' and not trigger_enemy.entered:
                    return False
                elif self.trigger_type == 'terminated' and not trigger_enemy.terminated:
                    return False
            else:
                # Default trigger is an entry of the previous enemy.
                trigger_enemy = self.game.enemies.first(
                    lambda x: x.entry_index == self.entry_index - 1 and x.route.id == self.route.id)
                if trigger_enemy and not trigger_enemy.entered:
                    return False

            if self.wait > 0:
                self.wait -= 1
                return

            self.entered = True

        return True

    def _move(self):
        if self.pos == self.next_pos:
            self.current_waypoint = self.next_waypoint
            self.next_waypoint = self.route.get_next_waypoint(self.current_waypoint)
            if self.next_waypoint:
                # Found the next point.
                self.next_pos = \
                    self.next_waypoint.x + random.randint(-10, 10), self.next_waypoint.y + random.randint(-10, 10)
            if not self.next_waypoint:
                self.terminate()
                self.game.life -= 1
        elif not self.blocked_unit:
            target_vec = mu.sub(self.next_pos, self.pos)
            # In order to move smoothly.
            if mu.magnitude(target_vec) < 2:
                self.pos = self.next_pos
                return
            move_vec = mu.scalar_mul(mu.normalize(target_vec), self.speed)
            self.x, self.y = mu.add(self.pos, move_vec)

    def update(self, *args):
        if self.terminated:
            return

        if not self._enter():
            return

        self._move()
        self.attack()

        super().update(self, *args)

    def find_attack_target(self):
        return self.game.find_closest_unit(self.pos, self.attack_range)

    def on_unit_terminated(self):
        self.blocked_unit = None

    def terminate(self):
        if self.blocked_unit:
            self.blocked_unit.on_enemy_terminated(self)
        super().terminate()
