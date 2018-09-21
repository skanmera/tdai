#!/usr/bin/python
# -*- coding: utf-8 -*-


__author__ = "skanmera"
__copyright__ = "Copyright 2018, skanmera"


import os
from .sprite import Sprite
from ..common.utils import MathUtil as mu


class Bullet(Sprite):

    def __init__(self, game, bullet_type, power, speed, owner, target):
        super().__init__(game=game,
                         filename=os.path.join(os.path.dirname(__file__),
                                               '../../assets/images/bullets/{}.png'.format(bullet_type)))
        self.type = bullet_type
        self.power = power
        self.target = target
        self.owner = owner
        self.pos = owner.pos
        self.speed = speed

    def update(self, *args):
        target_vector = mu.sub(self.target.pos, self.pos)
        if mu.magnitude(target_vector) < self.target.w / 2:
            self.impact()
        else:
            move_vec = mu.scalar_mul(mu.normalize(target_vector), self.speed)
            self.x, self.y = mu.add(self.pos, move_vec)

        super().update(self, *args)

    def impact(self):
        self.target.on_damaged(damage=self.power,
                               effect_image=os.path.join(os.path.dirname(__file__),
                                                         '../../assets/images/effects/{}.png'.format(self.type)))
        self.terminate()
