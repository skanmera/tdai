# -*- coding: utf-8 -*-


import os
import threading
from threading import Lock
from datetime import datetime
import numpy as np
import tensorflow as tf
import keras.backend as K
import matplotlib.pyplot as plt
from ..game.game import Game
from .map_network import MapNetwork
from .unit_network import UnitNetwork
from .slave import Slave


class Master(object):

    def __init__(self,
                 training_target,
                 game_params,
                 slave_count,
                 max_epoch,
                 graph_file_name,
                 export_trainable_vars_file,
                 import_trainable_vars_file,
                 drawing_graph_interval,
                 save_trainable_vars_interval):
        self.training_target = training_target
        self.game_params = game_params
        Game.init()
        self.game = Game(fps=game_params.fps,
                         speed=game_params.speed,
                         rendering=False,
                         training_interval=game_params.training_interval,
                         max_step=game_params.max_step,
                         blank_action_count=game_params.blank_action_count,
                         request_action_func=None,
                         send_action_result_func=None)
        self.game.load_level(game_params.level)
        self.slave_count = slave_count
        self.max_epoch = max_epoch
        self.initial_state = self.game.state
        self.slaves = {}
        self.epoch = 0
        default_file = datetime.now().strftime('%Y%m%d%H%M%S')
        self.graph_file = graph_file_name if graph_file_name else default_file
        self.export_trainable_vars_file = export_trainable_vars_file if export_trainable_vars_file else default_file
        self.import_trainable_vars_file = import_trainable_vars_file if import_trainable_vars_file else default_file
        self.kills = []
        self.total_kills = []
        self.drawing_graph_interval = drawing_graph_interval
        self.save_trainable_vars_interval = save_trainable_vars_interval
        self.sess = tf.Session()
        K.set_session(self.sess)
        self.lock = Lock()
        if self.training_target == 'unit':
            input_state_shape = np.concatenate([self.game.state.unit_hp_distribution,
                                                self.game.state.enemy_hp_distribution],
                                               axis=0).shape
            input_location_shape = (2, 10, 10)
            self.network = UnitNetwork(name='master',
                                       input_state_shape=input_state_shape,
                                       input_location_shape=input_location_shape,
                                       input_unit_shape=(1, 3),
                                       input_action_shape=(1, 3),
                                       filter_count=12,  # TODO: adjust
                                       filter_size=(3, 3))
        elif training_target == 'map':
            input_shape = np.concatenate([self.game.state.unit_id_distribution,
                                          self.game.state.enemy_id_distribution],
                                         axis=0).shape
            self.network = MapNetwork(name='master',
                                      input_shape=input_shape,
                                      action_count=len(self.game.actions),
                                      filter_count=12,  # TODO: adjust
                                      filter_size=(3, 3))
        self.network.build()

    def is_test(self):
        return self.epoch > self.max_epoch

    def run(self):
        tf.train.Coordinator()
        self.sess.run(tf.global_variables_initializer())

        try:
            if self.import_trainable_vars_file:
                self.network.model.load_weights(self.import_trainable_vars_file)
        except Exception as e:
            print(e)

        threads = []
        for i in range(self.slave_count):
            slave = Slave(master=self, name='slave_{}'.format(i))
            thread = threading.Thread(target=slave.run)
            thread.start()
            threads.append(thread)

        self.sess.run(tf.global_variables_initializer())

        # Master does not play the game.
        self.game.quite()

        while True:
            if self.epoch % self.drawing_graph_interval == 0:
                if self.kills:
                    self._draw_graph()
                    self._save_graph()
            if self.epoch % self.save_trainable_vars_interval == 0:
                self._save_weights()

    def _draw_graph(self):
        with self.lock:
            plt.clf()

            # Plot number of kills.
            self.total_kills.extend(self.kills)
            x = [x for x, _ in self.total_kills]
            y = [y for _, y in self.total_kills]
            plt.scatter(x, y, marker='.', s=1, c='r')

            # Draw Moving Average.
            num = 5
            b = np.ones(num) / num
            sma5 = np.convolve(y, b, mode='same')
            plt.plot(sma5, c='b', label='sma5')

            plt.pause(0.5)
            self.kills.clear()

    def _save_graph(self):
        if not os.path.isdir('graphs'):
            os.makedirs('graphs')
        plt.savefig('graphs/{}.png'.format(self.graph_file))

    def _save_weights(self):
        if not os.path.isdir('weights'):
            os.makedirs('weights')
        self.network.model.save_weights(os.path.join('weights/{}.hdf5'.format(self.export_trainable_vars_file)))


class GameInitializeParameter:
    """
    In order to give the slave game parameters through the pipe.
    Game object can't pickle.
    """

    def __init__(self, fps, speed, level, training_interval, max_step, blank_action_count):
        self.fps = fps
        self.speed = speed
        self.level = level
        self.training_interval = training_interval
        self.max_step = max_step
        self.blank_action_count = blank_action_count
