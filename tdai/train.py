#!/usr/bin/env python
# -*- coding: utf-8 -*-


__author__ = "skanmera"
__copyright__ = "Copyright 2018, skanmera"


import argparse
from datetime import datetime
from tdai.scripts.ai.master import Master
from tdai.scripts.ai.master import GameInitializeParameter


def parse_args():
    default_file = datetime.now().strftime('%Y%m%d%H%M%S')
    parser = argparse.ArgumentParser()
    parser.add_argument('--level', type=int, default=0)
    parser.add_argument('--target', type=str, default='map')
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--speed', type=int, default=10)
    parser.add_argument('--threads', type=int, default=8)
    parser.add_argument('--epoch', type=int, default=100000)
    parser.add_argument('--step', type=int, default=20)
    parser.add_argument('--blank', type=int, default=3)
    parser.add_argument('--graph', type=str, default=default_file)
    parser.add_argument('--import-vars', type=str, default=None)
    parser.add_argument('--export-vars', type=str, default=default_file)
    parser.add_argument('--action-interval', type=int, default=180)
    parser.add_argument('--draw-interval', type=int, default=100)
    parser.add_argument('--save-interval', type=int, default=100)
    args = parser.parse_args()

    return args


def main():
    args = parse_args()
    game_params = GameInitializeParameter(fps=args.fps,
                                          speed=args.speed,
                                          level=args.level,
                                          training_interval=args.action_interval,
                                          max_step=args.step,
                                          blank_action_count=args.blank)
    master = Master(training_target=args.target,
                    game_params=game_params,
                    slave_count=args.threads,
                    max_epoch=args.epoch,
                    graph_file_name=args.graph,
                    export_trainable_vars_file=args.export_vars,
                    import_trainable_vars_file=args.import_vars,
                    drawing_graph_interval=args.draw_interval,
                    save_trainable_vars_interval=args.save_interval)
    master.run()


if __name__ == '__main__':
    main()
