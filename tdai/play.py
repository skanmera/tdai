#!/usr/bin/env python
# -*- coding: utf-8 -*-


__author__ = "skanmera"
__copyright__ = "Copyright 2018, skanmera"


import argparse
from tdai.scripts.game import Game


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--level', type=int, required=True)
    parser.add_argument('-f', '--fps', default=60)
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    Game.init()
    game = Game(args.fps)
    game.load_level(args.level)
    game.play()


if __name__ == '__main__':
    main()
