# -*- coding: utf-8 -*-


__author__ = "skanmera"
__copyright__ = "Copyright 2018, skanmera"


import os
import sys
import pygame
from pygame.locals import *
import pytmx
import numpy as np
from .sprite import SpriteContainer
from .map import Location
from .map import Route
from .enemy import Enemy
from .unit import Unit
from ..common.utils import MathUtil as mu
from ..common.utils import CollectionUtil as cu


class Action(object):

    def __init__(self,
                 action_id,
                 action_type,
                 step=None,
                 unit_param=None,
                 location_param=None):
        self.id = action_id
        self.step = step
        self.type = action_type
        self.unit_param = unit_param
        self.location_param = location_param


class UnitParameter(object):

    def __init__(self, unit_id, unit_type, hp, attack_power, block_count):
        self.id = unit_id
        self.type = unit_type
        self.hp = hp
        self.attack_power = attack_power
        self.block_count = block_count


class LocationParameter(object):

    def __init__(self, location_id, location_type, pos):
        self.id = location_id
        self.type = location_type
        self.pos = pos


class ActionResult(object):

    def __init__(self, step, state, action, next_state, kills, killed, lost_life, is_terminal):
        self.step = step
        self.state = state
        self.action = action
        self.next_state = next_state
        self.kills = kills
        self.killed = killed
        self.lost_life = lost_life
        self.is_terminal = is_terminal


class GameSnapshot(object):

    def __init__(self, step):
        self.step = step
        self.life = 0
        self.cost = 0
        self.kills = 0
        self.killed = 0
        self.action = None
        self.state = None


class GameState(object):

    def __init__(self,
                 unit_id_distribution=None,
                 unit_type_distribution=None,
                 unit_hp_distribution=None,
                 unit_attack_power_distribution=None,
                 enemy_id_distribution=None,
                 enemy_type_distribution=None,
                 enemy_hp_distribution=None,
                 enemy_attack_power_distribution=None,
                 enemy_speed_distribution=None):
        self.unit_id_distribution = unit_id_distribution
        self.unit_type_distribution = unit_type_distribution
        self.unit_hp_distribution = unit_hp_distribution
        self.unit_attack_power_distribution = unit_attack_power_distribution
        self.enemy_id_distribution = enemy_id_distribution
        self.enemy_type_distribution = enemy_type_distribution
        self.enemy_hp_distribution = enemy_hp_distribution
        self.enemy_attack_power_distribution = enemy_attack_power_distribution
        self.enemy_speed_distribution = enemy_speed_distribution


class Game(object):

    def __init__(self,
                 fps=60,
                 speed=1.0,
                 rendering=True,
                 training_interval=0,
                 max_step=0,
                 blank_action_count=0,
                 request_action_func=None,
                 send_action_result_func=None):
        """
        Constructor
        :param fps: Frame Per Second.
        :param speed: Game speed.
        :param training_interval: Training parameter. Interval of action.
        :param max_step: Training parameter. Maximum number of times to train(do an action).
        :param blank_action_count: Training parameter. The number of actions which will do nothing included in one step.
        :param rendering: Whether to render window.
        :param request_action_func: Set the function to select an action by the policy.
        :param send_action_result_func: Set the function to send the result of the action taken.
        """
        self.screen = pygame.display.set_mode((0, 0))
        self.fps = fps
        self.speed = speed
        self.rendering = rendering
        self.training_interval = training_interval
        self.max_step = max_step
        self.blank_action_count = blank_action_count
        self.screen = None
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 30)
        self.level = 0
        self.frame = 0
        self.tmx = None
        self.snapshots = {}
        self.cost = 0
        self.life = 50
        self.kills = 0
        self.killed = 0
        self.enemies = SpriteContainer()
        self.units = SpriteContainer()
        self.locations = SpriteContainer()
        self.routes = []
        self.bullets = SpriteContainer()
        self.effects = SpriteContainer()
        self.dragging_unit = None
        self.step = 0
        self.state = None
        self.action = None
        self.actions = []
        self.request_action_func = request_action_func
        self.send_action_result_func = send_action_result_func

    @staticmethod
    def init():
        """
        Initialize pygame.
        """
        pygame.init()
        pygame.font.init()

    @staticmethod
    def quite():
        """
        Finalize pygame.
        """
        pygame.display.quit()
        pygame.quit()

    def load_level(self, level):
        """
        Load the specified level from tmx file.
        """
        self._initialize()
        self.level = level
        self._load_level()

        # In order to initialize master's network, call these methods.
        self._scan_actions()
        self._observe()

    def reset_level(self):
        """
        Reset to play the current level again.
        """
        self.load_level(self.level)

    def play(self):
        self.step = 0
        while True:
            self.clock.tick(self.fps * self.speed)

            # Check if the window has been closed by the closing button or not.
            if self._is_quit():
                pygame.quit()
                sys.exit()

            if self.training_interval > 0 and self.frame > 0 and self.frame % self.training_interval == 0:
                self._observe()
                self._training(terminal=False)

            self._handle_mouse_event()
            self._update()
            self._render()

            if self._is_finished():
                break

            if self.frame % self.fps == 0:
                self.cost += 1

            self.frame += 1

        self._training(terminal=True)

    @staticmethod
    def _is_quit():
        for event in pygame.event.get():
            if event.type == QUIT:
                return True
        return False

    def _scan_actions(self):
        self.actions.clear()
        action_id = 0
        step = 0

        # Add blank actions.
        for _ in range(self.max_step):
            for _ in range(self.blank_action_count):
                self.actions.append(Action(action_id=action_id,
                                           action_type='none',
                                           step=step))
                action_id += 1
            step += 1

        # Add sortieing and withdrawing.
        for location in self.locations.enumerate():
            location_param = LocationParameter(location_id=location.id,
                                               location_type=location.type,
                                               pos=location.pos)
            if location.type == 'melee':
                for unit in self.units.enumerate():
                    unit_param = UnitParameter(unit_id=unit.id,
                                               unit_type=unit.type,
                                               hp=unit.hp,
                                               attack_power=unit.attack_power,
                                               block_count=unit.block_count)
                    if unit.battle_style == 'melee':
                        self.actions.append(Action(action_id=action_id,
                                                   action_type='sortie',
                                                   unit_param=unit_param,
                                                   location_param=location_param))
                        action_id += 1
                        self.actions.append(Action(action_id=action_id,
                                                   action_type='withdraw',
                                                   unit_param=unit_param,
                                                   location_param=location_param))
                        action_id += 1
            elif location.type == 'ranged':
                for unit in self.units.enumerate():
                    unit_param = UnitParameter(unit_id=unit.id,
                                               unit_type=unit.type,
                                               hp=unit.hp,
                                               attack_power=unit.attack_power,
                                               block_count=unit.block_count)
                    if unit.battle_style == 'ranged':
                        self.actions.append(Action(action_id=action_id,
                                                   action_type='sortie',
                                                   unit_param=unit_param,
                                                   location_param=location_param))
                        action_id += 1
                        self.actions.append(Action(action_id=action_id,
                                                   action_type='withdraw',
                                                   unit_param=unit_param,
                                                   location_param=location_param))
                        action_id += 1

    def _is_enabled_action(self, action):
        if action.type == 'none':
            if self.step >= 0:
                return action.step == self.step
            else:
                return True
        unit = self.units.first(lambda x: x.id == action.unit_param.id)
        if not unit:
            return False
        location = self.locations.first(lambda x: x.id == action.location_param.id)
        if not location:
            return False
        if unit.withdrawn or unit.terminated:
            return False
        if action.type == 'sortie':
            if unit.sortied:
                return False
            if self.cost < unit.cost:
                return False
            if location.unit:
                return False
        elif action.type == 'withdraw':
            if not location.unit:
                return False
            if unit is not location.unit:
                return False
        return True

    def _do_action(self, action):
        if not action or action.type == 'none':
            return
        unit = self.units.first(lambda x: x.id == action.unit_param.id)
        if not unit:
            return
        location = self.locations.first(lambda x: x.id == action.location_param.id)
        if not location:
            return
        if action.type == 'sortie':
            unit.sortie(location)
        elif action.type == 'withdraw':
            unit.withdraw()

    def _observe(self):
        unit_id_distribution = self._observe_unit_id_distribution()
        unit_hp_distribution = self._observe_unit_hp_distribution()
        enemy_id_distribution = self._observe_enemy_id_distribution()
        enemy_hp_distribution = self._observe_enemy_hp_distribution()
        self.state = GameState(unit_id_distribution=unit_id_distribution,
                               unit_hp_distribution=unit_hp_distribution,
                               enemy_id_distribution=enemy_id_distribution,
                               enemy_hp_distribution=enemy_hp_distribution)

    def _observe_unit_hp_distribution(self):
        # Put hp distribution of units into 10x10 matrix.
        distribution = np.zeros((1, 10, 10), dtype=float)
        for unit in self.units.enumerate():
            if unit.sortied and not unit.terminated:
                x, y = int(unit.pos[0] / 64), int(unit.pos[1] / 64)
                distribution[0, x, y] += unit.hp / 1000
        return distribution

    def _observe_enemy_hp_distribution(self):
        # Put hp distribution of enemies into 10x10 matrix.
        distribution = np.zeros((1, 10, 10), dtype=float)
        for enemy in self.enemies.enumerate():
            if enemy.entered and not enemy.terminated:
                x, y = int(enemy.pos[0] / 64), int(enemy.pos[1] / 64)
                if x < 10 and y < 10:
                    distribution[0, x, y] += enemy.hp / 1000
        return distribution

    def _observe_unit_id_distribution(self):
        # Put id distribution of units into 10x10 matrix.
        distribution = np.zeros((self.units.len(), 10, 10), dtype=int)
        i = 0
        for unit in self.units.enumerate():
            if unit.sortied:
                x, y = int(unit.pos[0] / 64), int(unit.pos[1] / 64)
                distribution[i, x, y] = 1
                i += 1
        return distribution

    def _observe_enemy_id_distribution(self):
        # Put id distribution of enemies into 10x10 matrix.
        distribution = np.zeros((self.enemies.len(), 10, 10), dtype=int)
        i = 0
        for enemy in self.enemies.enumerate():
            if enemy.entered and not enemy.terminated:
                x, y = int(enemy.pos[0] / 64), int(enemy.pos[1] / 64)
                if x < 10 and y < 10:
                    distribution[i, x, y] = 1
                i += 1
        return distribution

    def _load_level(self):
        self.tmx = pytmx.load_pygame(
            os.path.join(os.path.dirname(__file__), '../../assets/maps/{0:03d}.tmx'.format(self.level)))
        self.screen = pygame.display.set_mode(
            (self.tmx.tilewidth * self.tmx.width, self.tmx.tileheight * self.tmx.height))
        self._load_locations()
        self._load_routes()
        self._load_enemies()
        self._load_units()

    def _load_locations(self):
        self.locations.extend(map(lambda x: Location(game=self, obj=x), self.tmx.get_layer_by_name('locations')))

    def _load_routes(self):
        self.routes = list(map(lambda x: Route(x), filter(lambda l: 'route' in l.name, self.tmx.layers)))

    def _load_enemies(self):
        enemies_layers = filter(lambda l: 'enemies' in l.name, self.tmx.layers)
        for layer in enemies_layers:
            route_id = int(layer.route)
            layer = sorted(layer, key=lambda x: x.entry_index, reverse=True)
            for obj in layer:
                route = cu.first_or_default(self.routes, predicate=lambda r: r.id == route_id)
                self.enemies.append(Enemy(game=self, route=route, tmx_obj=obj))

    def _load_units(self):
        for obj in self.tmx.get_layer_by_name('units'):
            self.units.append(Unit.create(game=self, tmx_obj=obj))

    def _initialize(self):
        self.frame = 0
        self.tmx = None
        self.life = 50
        self.cost = 0
        self.kills = 0
        self.killed = 0
        self.snapshots.clear()
        self.enemies.clear()
        self.units.clear()
        self.locations.clear()
        self.routes.clear()
        self.bullets.clear()
        self.effects.clear()
        self.state = None
        self.step = 0

    def _is_finished(self):
        return self.enemies.all(lambda x: x.terminated)

    def _update(self):
        self.locations.update()
        self.units.update()
        self.enemies.update()
        self.bullets.update()
        self.bullets.remove_all_terminated()
        self.effects.update()

    def _render(self):
        if not self.rendering:
            return
        # Draw terrain.
        for x, y, gid, in self.tmx.get_layer_by_name('terrain'):
            tile = self.tmx.get_tile_image_by_gid(gid)
            self.screen.blit(tile, (x * self.tmx.tilewidth, y * self.tmx.tileheight))
        # Draw sprites.
        self.locations.draw()
        self.units.draw()
        self.enemies.draw()
        self.bullets.draw()
        self.effects.draw()
        # Draw cost, life and etc...
        self._render_labels()

        pygame.display.update()

    def _render_labels(self):
        life = self.font.render('L{}'.format(self.life), False, (0, 0, 255))
        self.screen.blit(life, (0, 0))
        kills = self.font.render('E{}'.format(self.kills), False, (0, 255, 0))
        self.screen.blit(kills, (0, 32))
        killed = self.font.render('U{}'.format(self.killed), False, (255, 0, 0))
        self.screen.blit(killed, (0, 64))
        cost = self.font.render('C{}'.format(self.cost), False, (0, 0, 0))
        self.screen.blit(cost, (0, self.tmx.height * self.tmx.tileheight - 80))

        # Draw required consts on units.
        for unit in self.units.enumerate():
            if not unit.sortied and not self.dragging_unit == unit and not unit.terminated:
                cost_color = (0, 145, 197) if unit.battle_style == 'ranged' else (254, 146, 23)
                unit_cost = self.font.render('{}'.format(unit.cost), False, cost_color)
                self.screen.blit(unit_cost, (unit.pos[0], unit.pos[1] - 32))

    def _handle_mouse_event(self):
        if not pygame.mouse.get_focused():
            self._set_dragging_unit()
            return
        x, y = pygame.mouse.get_pos()
        pressed = pygame.mouse.get_pressed()
        # Left click and drag to sortie units.
        if pressed[0]:
            if self.dragging_unit:
                self.dragging_unit.pos = (x, y)
            else:
                self.dragging_unit = self._hit_unit((x, y))
                if self.dragging_unit:
                    self.dragging_unit.current_pos = self.dragging_unit.pos
        # Right click to withdraw units.
        elif pressed[2]:
            self._set_dragging_unit()
            hit_unit = self._hit_unit((x, y))
            if hit_unit and hit_unit.sortied and not hit_unit.terminated:
                hit_unit.withdraw()
        else:
            self._set_dragging_unit()

    def _append_snapshot(self):
        snapshot = GameSnapshot(self.step)
        snapshot.life = self.life
        snapshot.cost = self.cost
        snapshot.kills = self.kills
        snapshot.killed = self.killed
        snapshot.action = self.action
        snapshot.state = self.state
        self.snapshots[self.step] = snapshot

    def _training(self, terminal):
        if not self.request_action_func or not self.send_action_result_func:
            return

        self._send_action_result(is_terminal=terminal)

        enabled_actions = [x for x in self.actions if self._is_enabled_action(x)]
        if not enabled_actions:
            return

        self.action = self.request_action_func(self.step, self.state, enabled_actions)
        self._append_snapshot()
        self._do_action(self.action)
        self.step += 1

    def _send_action_result(self, is_terminal):
        if self.step - 1 not in self.snapshots:
            return

        snapshot = self.snapshots[self.step - 1]
        action_result = ActionResult(step=snapshot.step,
                                     state=snapshot.state,
                                     action=snapshot.action,
                                     next_state=self.state,
                                     kills=self.kills - snapshot.kills,
                                     killed=self.killed - snapshot.killed,
                                     lost_life=snapshot.life - self.life,
                                     is_terminal=is_terminal)
        self.send_action_result_func(action_result)

    def find_closest_unit(self, pos, scope):
        closest_unit = None
        min_distance = scope
        for unit in self.units.enumerate():
            if unit.terminated or not unit.sortied:
                continue
            distance = mu.magnitude(mu.sub(unit.pos, pos))
            if distance < min_distance:
                closest_unit = unit
                min_distance = distance
        return closest_unit

    def find_closest_enemy_to_goal(self, pos, scope):
        closest_enemy = None
        min_distance = None
        for enemy in self.enemies.enumerate():
            if enemy.terminated or not enemy.entered:
                continue
            distance = mu.magnitude(mu.sub(enemy.pos, pos))
            if distance < scope:
                goal_pos = (enemy.route.goal.x, enemy.route.goal.y)
                distance_goal = mu.magnitude(mu.sub(enemy.pos, goal_pos))
                if not min_distance or distance_goal < min_distance:
                    closest_enemy = enemy
                    min_distance = distance_goal
        return closest_enemy

    def enumerate_within_enemies(self, pos, scope):
        for enemy in self.enemies.enumerate():
            if enemy.terminated:
                continue
            distance_to_pos = mu.magnitude(mu.sub(enemy.pos, pos))
            if distance_to_pos < scope:
                yield enemy

    def _hit_unit(self, pos):
        for unit in self.units.enumerate():
            if unit.terminated:
                continue
            distance = mu.magnitude(mu.sub(unit.pos, pos))
            if distance < 10:
                return unit

    def _hit_location(self, pos):
        for location in self.locations.enumerate():
            if location.unit:
                continue

            distance = mu.magnitude(mu.sub(location.pos, pos))
            if distance < 20:
                return location

    def _set_dragging_unit(self):
        if not self.dragging_unit:
            return

        if not self.dragging_unit.sortied:
            location = self._hit_location(pygame.mouse.get_pos())
            if location:
                if self.dragging_unit.sortie(location):
                    self.dragging_unit.current_pos = self.dragging_unit.pos

        self.dragging_unit.pos = self.dragging_unit.current_pos
        self.dragging_unit = None

    def on_battle_object_killed(self, battle_object):
        if isinstance(battle_object, Unit):
            self.killed += 1
        elif isinstance(battle_object, Enemy):
            self.kills += 1
