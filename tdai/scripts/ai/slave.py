# -*- coding: utf-8 -*-


from multiprocessing import Process
from multiprocessing import Pipe
import tensorflow as tf
import numpy as np
import random
from ..game.game import Game
from ..common.utils import ConsoleUtil as cu
from ..common.utils import ConsoleColor as cc


ADVANTAGE_STEPS = 5
GAMMA = 0.99
MIN_BATCH = 5
GAME_EVENT_TYPE_NONE = 0
GAME_EVENT_TYPE_REQUEST_ACTION = 1
GAME_EVENT_TYPE_SEND_RESULT = 2
GAME_EVENT_TYPE_EPOCH_FINISHED = 3


class Slave(object):

    def __init__(self, master, name):
        self.master = master
        self.name = name
        self.network = self.master.network.clone(self.name)
        self.network.build()
        self.epoch = 0
        self.total_reward = 0
        self.memory = []
        self.R = 0
        self.train_queue = []
        self.apply_gradients_op = None
        self.copy_trainable_vars_op = None
        self._build_graph()

    def _build_graph(self):
        with tf.name_scope(self.name):
            self.apply_gradients_op = self.master.network.get_optimizer_op.apply_gradients(
                zip(self.network.get_gradients_op, self.master.network.get_trainable_variables_op))

            self.copy_trainable_vars_op = [dst.assign(src) for dst, src in zip(
                self.network.get_trainable_variables_op, self.master.network.get_trainable_variables_op)]

    def select_action(self, step, state, enabled_actions):
        if not enabled_actions:
            return None

        # Use ε-greedy algorithm.
        epsilon = 0.1 + 0.9 / (1.0 + (self.epoch / 10))
        use_random = not self.master.is_test() and epsilon >= np.random.uniform(0, 1)

        if step == 0 and self.is_main_slave():
            cu.print_color('##### epoch {} #####'.format(self.epoch), cc.YELLOW)
            if self.master.is_test():
                cu.print_color('test', cc.BLUE)
            else:
                cu.print_color('ε={}'.format(epsilon), cc.BLUE)

        selected_action = None
        if use_random:
            selected_action = random.choice(enabled_actions)
        elif self.master.training_target == 'map':
            selected_action = self._select_action_map_mode(state, enabled_actions)
        elif self.master.training_target == 'unit':
            selected_action = self._select_action_unit_mode(state, enabled_actions)

        return selected_action

    def _select_action_map_mode(self, state, enabled_actions):
        id_distribution = np.concatenate([state.unit_id_distribution, state.enemy_id_distribution], axis=0)
        probabilities, _ = self.network.model.predict(np.array([id_distribution]))

        # Adjust probabilities so as to be selected only enabled actions.
        enabled_probabilities = np.zeros(probabilities[0].shape)
        for action in enabled_actions:
            enabled_probabilities[action.id] = probabilities[0][action.id]
        probabilities_sum = sum(enabled_probabilities)

        # If sum of enabled probabilities is zero, chose random.
        if probabilities_sum == 0:
            return random.choice(enabled_actions)

        # Adjust probabilities so that sum of probabilities is 1.
        for action in enabled_actions:
            enabled_probabilities[action.id] = enabled_probabilities[action.id] / probabilities_sum

        if self.master.is_test():
            # Select max when test mode.
            selected_action_id = np.argmax(enabled_probabilities)
        else:
            # Select following probability when training mode.
            selected_action_id = np.random.choice(self.network.action_count, p=enabled_probabilities)

        selected_action = [x for x in enabled_actions if x.id == selected_action_id][0]

        return selected_action

    def _select_action_unit_mode(self, state, enabled_actions):
        input_state = np.array([np.concatenate([state.unit_hp_distribution,
                                                state.enemy_hp_distribution])])
        selected_action = None
        max_value = None
        for action in enabled_actions:
            pos = np.zeros((2, 10, 10), dtype=int)
            if action.location_param:
                x, y = int(action.location_param.pos[0] / 64), int(action.location_param.pos[1] / 64)
                dim = 0 if action.location_param.type == 'melee' else 1
                pos[dim, x, y] = 1
            input_location = np.array([pos])

            unit = [0, 0, 0]
            if action.unit_param:
                unit = [action.unit_param.hp / 100,
                        action.unit_param.attack_power / 100,
                        action.unit_param.block_count / 5]
            input_unit = np.array([[unit]], dtype=float)

            action_type_id = 0
            if action.type == 'sortie':
                action_type_id = 1
            elif action.type == 'withdraw':
                action_type_id = 2
            input_action = [0, 0, 0]
            input_action[action_type_id] = 1
            input_action = np.array([[input_action]], dtype=int)

            value = self.network.model.predict([input_state, input_location, input_unit, input_action])
            if not selected_action or value > max_value:
                selected_action = action
                max_value = value

        return selected_action

    def _calc_reward(self, action_result):
        max_reward = self.master.game.enemies.len()
        return (action_result.kills - action_result.lost_life) / max_reward

    def receive_action_result(self, action_result):
        self.total_reward += action_result.kills

        if not self.master.is_test():
            self.memory.append(action_result)

            r = self._calc_reward(action_result)
            self.R = (self.R + r * GAMMA ** ADVANTAGE_STEPS) / GAMMA

            if action_result.is_terminal:
                while len(self.memory) > 0:
                    self.train_queue.append(self._sample_memory(len(self.memory)))
                    self.R = (self.R - self._calc_reward(self.memory[0])) / GAMMA
                    self.memory.pop(0)
            elif len(self.memory) >= ADVANTAGE_STEPS:
                self.train_queue.append(self._sample_memory(ADVANTAGE_STEPS))
                self.memory.pop(0)

            if action_result.is_terminal or action_result.step % ADVANTAGE_STEPS == 0:
                self._sync()

        if action_result.is_terminal:
            with self.master.lock:
                self.master.kills.append((self.epoch, self.total_reward))
                self.master.epoch += 1
                self.epoch = self.master.epoch
            self.total_reward = 0
            self.memory.clear()
            self.train_queue.clear()
            self.R = 0

    def _sync(self):
        if len(self.train_queue) < MIN_BATCH:
            return

        if self.master.training_target == 'unit':
            self._apply_gradients_on_unit_mode()
        elif self.master.training_target == 'map':
            self._apply_gradients_on_map_mode()

        with self.master.lock:
            self.master.sess.run(self.copy_trainable_vars_op)

        self.train_queue.clear()

    def _apply_gradients_on_map_mode(self):
        for s_t, a_t, r, s_tn, terminal in self.train_queue:

            id_distribution_ = np.concatenate([s_tn.unit_id_distribution, s_tn.enemy_id_distribution], axis=0)
            _, v = self.network.model.predict(np.array([id_distribution_]))
            v_tn = r + (GAMMA ** ADVANTAGE_STEPS) * v * (not terminal)

            id_distribution = np.concatenate([s_t.unit_id_distribution, s_t.enemy_id_distribution], axis=0)
            input_state = np.array([id_distribution])

            action_vec = np.zeros(self.network.action_count, dtype=float)
            for i in range(self.network.action_count):
                action_vec[i] = 1.0 if i == a_t.id else 1e-10
            output_policy = np.array([action_vec])

            output_v = np.array(v_tn)

            feed_dict = {self.network.input_state_ph: input_state,
                         self.network.output_policy_ph: output_policy,
                         self.network.output_state_value_ph: output_v}

            with self.master.lock:
                self.master.sess.run(self.apply_gradients_op, feed_dict=feed_dict)

    def _apply_gradients_on_unit_mode(self):
        for s, a, r, s_, t in self.train_queue:
            input_state_ = np.array([np.concatenate([s_.unit_hp_distribution,
                                                     s_.enemy_hp_distribution])])
            pos = np.zeros((2, 10, 10), dtype=int)
            input_location_ = np.array([pos])
            input_unit_ = np.array([[[0, 0, 0]]], dtype=float)
            input_action_ = np.array([[[0, 0, 0]]], dtype=int)
            value = self.network.model.predict([input_state_,
                                                input_location_,
                                                input_unit_,
                                                input_action_])

            v_n = r + (GAMMA ** ADVANTAGE_STEPS) * value * (not t)

            input_state = np.array([np.concatenate([s.unit_hp_distribution,
                                                    s.enemy_hp_distribution])])
            pos = np.zeros((2, 10, 10), dtype=int)
            if a.location_param:
                x, y = int(a.location_param.pos[0] / 64), int(a.location_param.pos[1] / 64)
                pos[0, x, y] = 1
            input_location = np.array([pos])

            unit = [0, 0, 0]
            if a.unit_param:
                unit = [a.unit_param.hp / 100,
                        a.unit_param.attack_power / 100,
                        a.unit_param.block_count / 5]
            input_unit = np.array([[unit]], dtype=float)

            action_type_id = 0
            if a.type == 'sortie':
                action_type_id = 1
            elif a.type == 'withdraw':
                action_type_id = 2
            input_action = [0, 0, 0]
            input_action[action_type_id] = 1
            input_action = np.array([[input_action]], dtype=int)

            output_v = np.array(v_n)

            feed_dict = {self.network.input_state_ph: input_state,
                         self.network.input_location_ph: input_location,
                         self.network.input_unit_ph: input_unit,
                         self.network.input_action_ph: input_action,
                         self.network.output_value_ph: output_v}
            with self.master.lock:
                self.master.sess.run(self.apply_gradients_op, feed_dict=feed_dict)

    def _sample_memory(self, n):
        s = self.memory[0].state
        a = self.memory[0].action
        r = self.R
        s_ = self.memory[n - 1].state
        t = self.memory[n - 1].is_terminal
        return s, a, r, s_, t

    def is_main_slave(self):
        return self.name == 'slave_0'

    def run(self):
        self.master.sess.run(self.copy_trainable_vars_op)
        conn, worker_conn = Pipe()
        process = Process(target=GameWorker.run, args=(worker_conn, self.master.game_params,))
        process.start()
        while True:
            message = conn.recv()
            event = message[0]
            if event == GAME_EVENT_TYPE_REQUEST_ACTION:
                action = self.select_action(message[1], message[2], message[3])
                conn.send([action])
            elif event == GAME_EVENT_TYPE_SEND_RESULT:
                self.receive_action_result(message[1])
                conn.send([])


class GameWorker(object):

    def __init__(self, conn, game):
        self.game = game
        self.conn = conn

    def _request_action(self, step, state, enabled_actions):
        self.conn.send([GAME_EVENT_TYPE_REQUEST_ACTION, step, state, enabled_actions])
        return self.conn.recv()[0]

    def _send_action_result(self, action_result):
        self.conn.send([GAME_EVENT_TYPE_SEND_RESULT, action_result])
        self.conn.recv()

    def _run(self):
        while True:
            self.game.request_action_func = self._request_action
            self.game.send_action_result_func = self._send_action_result
            self.game.play()
            self.game.reset_level()

    @staticmethod
    def run(conn, game_params):
        Game.init()
        game = Game(fps=game_params.fps,
                    speed=game_params.speed,
                    rendering=True,
                    training_interval=game_params.training_interval,
                    max_step=game_params.max_step,
                    blank_action_count=game_params.blank_action_count,
                    request_action_func=None,
                    send_action_result_func=None)
        game.load_level(game_params.level)
        worker = GameWorker(conn=conn, game=game)
        worker._run()
