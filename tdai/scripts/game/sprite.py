# -*- coding: utf-8 -*-


__author__ = "skanmera"
__copyright__ = "Copyright 2018, skanmera"


import pygame
from pygame.locals import *
from ..common.utils import CollectionUtil as cu


class Sprite(pygame.sprite.Sprite):

    def __init__(self, game, filename=None, image=None, x=0, y=0):
        self.game = game
        pygame.sprite.Sprite.__init__(self)
        if image:
            self.image = image.convert_alpha()
        else:
            self.image = pygame.image.load(filename).convert_alpha()
        self.w = self.image.get_width()
        self.h = self.image.get_height()
        self.x = float(x)
        self.y = float(y)
        self.terminated = False

    @property
    def pos(self):
        return self.x, self.y

    @pos.setter
    def pos(self, pos):
        self.x = pos[0]
        self.y = pos[1]

    def draw(self):
        if not self.terminated:
            rect = Rect(self.x - self.w / 2.0, self.y - self.h / 2, self.w, self.h)
            self.game.screen.blit(self.image, rect)

    def terminate(self):
        self.terminated = True
        self.kill()


class SpriteContainer(object):

    def __init__(self):
        self.sprites = []

    def len(self):
        return len(self.sprites)

    def enumerate(self):
        for s in self.sprites:
            yield s

    def any(self, predicate=None):
        return any(predicate(x) for x in self.sprites) if predicate else self.len() > 0

    def empty(self):
        return not self.any()

    def all(self, predicate):
        return all(predicate(x) for x in self.sprites)

    def first(self, predicate):
        return cu.first_or_default(self.sprites, default=None, predicate=predicate)

    def append(self, sprite):
        self.sprites.append(sprite)

    def extend(self, sprites):
        self.sprites.extend(sprites)

    def remove(self, sprite):
        self.sprites.remove(sprite)

    def update(self):
        for s in self.sprites:
            s.update()

    def remove_all_terminated(self):
        for i in [x for x in self.sprites if x.terminated]:
            self.remove(i)

    def draw(self):
        for s in self.sprites:
            if not s.terminated:
                s.draw()

    def clear(self):
        for s in self.sprites:
            s.terminate()
        self.sprites.clear()
