# -*- coding: utf-8 -*-


__author__ = "skanmera"
__copyright__ = "Copyright 2018, skanmera"


import math


class ConsoleColor(object):
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'


class ConsoleUtil(object):
    @staticmethod
    def print_color(s, color):
        end = '\033[0m'
        print(color + s + end)


class CollectionUtil(object):

    @staticmethod
    def first_or_default(iterable, default=None, predicate=None):
        return next(filter(predicate, iterable), default)


class MathUtil(object):

    @staticmethod
    def magnitude(vec: tuple) -> float:
        return math.sqrt(sum(vec[i] * vec[i] for i in range(len(vec))))

    @staticmethod
    def add(vec1: tuple, vec2: tuple) -> tuple:
        return tuple([vec1[i] + vec2[i] for i in range(len(vec1))])

    @staticmethod
    def scalar_add(vec1: tuple, scalar: float) -> tuple:
        return tuple([vec1[i] + scalar for i in range(len(vec1))])

    @staticmethod
    def sub(vec1, vec2) -> tuple:
        return tuple([vec1[i] - vec2[i] for i in range(len(vec1))])

    @staticmethod
    def scalar_sub(vec1: tuple, scalar: float) -> tuple:
        return tuple([vec1[i] - scalar for i in range(len(vec1))])

    @staticmethod
    def scalar_mul(vec1: tuple, scalar: float) -> tuple:
        return tuple([vec1[i] * scalar for i in range(len(vec1))])

    @staticmethod
    def dot(vec1, vec2) -> float:
        return sum(vec1[i] * vec2[i] for i in range(len(vec1)))

    @staticmethod
    def normalize(vec) -> tuple:
        mag = MathUtil.magnitude(vec)
        return tuple([vec[i] / mag for i in range(len(vec))])



