# -*- coding: utf-8 -*-


__author__ = "skanmera"
__copyright__ = "Copyright 2018, skanmera"


from abc import ABCMeta, abstractclassmethod
from .battle_object import BattleObject


class Unit(BattleObject, metaclass=ABCMeta):

    def __init__(self, game, tmx_obj):
        super().__init__(game=game, tmx_obj=tmx_obj)
        self.cost = int(tmx_obj.cost)
        self.block_count = int(tmx_obj.block_count)
        self.battle_style = tmx_obj.battle_style
        self.sortied = False
        self.withdrawn = False
        self.location = None
        self.current_pos = self.pos

    @classmethod
    def create(cls, game, tmx_obj):
        if tmx_obj.battle_style == 'melee':
            return MeleeUnit(game, tmx_obj)
        elif tmx_obj.battle_style == 'ranged':
            return RangedUnit(game, tmx_obj)
        return None

    def update(self, *args):
        if self.terminated:
            return
        if self.sortied and not self.withdrawn:
            self.attack()
        super().update(self, *args)

    def sortie(self, location):
        if self.game.cost < self.cost:
            return False
        if self.sortied:
            return False
        if not location.try_put_unit(self):
            return False
        self.x = location.x
        self.y = location.y
        self.pos = location.pos
        self.sortied = True
        self.location = location
        self.game.cost -= self.cost
        return True

    def withdraw(self):
        if not self.sortied or self.withdrawn:
            return False
        self.withdrawn = True
        self.location.unit = None
        self.location.on_unit_withdrawn()
        self.location = None
        self.terminate()
        return True

    @abstractclassmethod
    def find_attack_target(self):
        pass

    def terminate(self):
        if self.location:
            self.location.on_unit_withdrawn()
            self.location = None
        super().terminate()


class RangedUnit(Unit):

    def __init__(self, game, tmx_obj):
        super().__init__(game=game, tmx_obj=tmx_obj)

    def find_attack_target(self):
        return self.game.find_closest_enemy_to_goal(self.pos, self.attack_range)


class MeleeUnit(Unit):

    def __init__(self, game, tmx_obj):
        super().__init__(game=game, tmx_obj=tmx_obj)
        self.block_enemies = []

    @property
    def blocked_count(self):
        return len(self.block_enemies)

    def update(self, *args):
        if self.terminated:
            return
        super().update(self, *args)
        self._block_enemy()

    def find_attack_target(self):
        if self.block_enemies:
            return self.block_enemies[0]
        else:
            return super().find_attack_target()

    def _block_enemy(self):
        if not self.sortied:
            return
        enemies = self.game.enumerate_within_enemies(self.pos, self.w)
        for enemy in enemies:
            can_block = self.block_count - self.blocked_count
            if can_block > 0 and not enemy.blocked_unit:
                enemy.blocked_unit = self
                self.block_enemies.append(enemy)

    def on_enemy_terminated(self, enemy):
        if enemy in self.block_enemies:
            self.block_enemies.remove(enemy)

    def terminate(self):
        for enemy in self.block_enemies:
            enemy.on_unit_terminated()
        self.block_enemies.clear()
        super().terminate()

