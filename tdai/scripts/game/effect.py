# -*- coding: utf-8 -*-


__author__ = "skanmera"
__copyright__ = "Copyright 2018, skanmera"


from .sprite import Sprite


class Effect(Sprite):

    def __init__(self, game, filename, target, duration=0.2):
        super().__init__(game=game, filename=filename, x=target.x, y=target.y)
        self.target = target
        self.duration = duration * game.fps

    def update(self, *args):
        if self.target and self.duration > 0:
            self.pos = self.target.pos
        else:
            self.terminate()

        self.duration -= 1

    def draw(self):
        if self.duration > 0:
            super().draw()

