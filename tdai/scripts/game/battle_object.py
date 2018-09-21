#!/usr/bin/python
# -*- coding: utf-8 -*-


__author__ = "skanmera"
__copyright__ = "Copyright 2018, skanmera"


from abc import ABCMeta, abstractclassmethod
from .sprite import Sprite
from .bullet import Bullet
from .effect import Effect


class BattleObject(Sprite, metaclass=ABCMeta):
    """
    Base class of enemy and unit.
    """

    def __init__(self, game, tmx_obj):
        super().__init__(game=game, image=tmx_obj.image, x=tmx_obj.x, y=tmx_obj.y)
        self.id = tmx_obj.id
        self.name = tmx_obj.name
        self.type = tmx_obj.type
        self.hp = int(tmx_obj.hp)
        self.attack_power = float(tmx_obj.attack_power)
        self.attack_speed = float(tmx_obj.attack_speed) * self.game.fps
        self.attack_wait = self.attack_speed
        self.attack_range = float(tmx_obj.attack_range)
        self.bullet = tmx_obj.bullet
        self.bullet_speed = float(tmx_obj.bullet_speed)

    @abstractclassmethod
    def find_attack_target(self):
        # Override in sub class.
        pass

    def attack(self):
        if self.attack_wait > 0:
            self.attack_wait -= 1
            return

        target = self.find_attack_target()
        if target:
            self.game.bullets.append(Bullet(game=self.game,
                                            bullet_type=self.bullet,
                                            power=self.attack_power,
                                            speed=self.bullet_speed,
                                            owner=self,
                                            target=target))

            # Reset waiting time.
            self.attack_wait = self.attack_speed

    def on_damaged(self, damage, effect_image):
        # Damage effect.
        self.game.effects.append(Effect(game=self.game,
                                        filename=effect_image,
                                        target=self))
        self.hp -= damage
        if self.hp <= 0:
            self.terminate()
            self.game.on_battle_object_killed(battle_object=self)
