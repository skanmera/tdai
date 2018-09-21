# -*- coding: utf-8 -*-


__author__ = "skanmera"
__copyright__ = "Copyright 2018, skanmera"


import tensorflow as tf
from keras.models import Model
from keras.layers import Input, Dense, Conv2D, Flatten


class MapNetwork(object):

    def __init__(self,
                 name,
                 input_shape,
                 action_count,
                 filter_count=1,
                 filter_size=(3, 3),
                 entropy_coefficient=.01,
                 learning_rate=5e-3):
        self.name = name
        self.input_shape = input_shape
        self.action_count = action_count
        self.filter_count = filter_count
        self.filter_size = filter_size
        self.entropy_coefficient = entropy_coefficient
        self.learning_rate = learning_rate
        self.model = None
        self.input_state_ph = None
        self.output_policy_ph = None
        self.output_state_value_ph = None
        self.get_trainable_variables_op = None
        self.get_gradients_op = None
        self.get_total_loss_op = None
        self.get_optimizer_op = None
        self.apply_gradients_op = None

    def clone(self, name):
        network = MapNetwork(name=name,
                             input_shape=self.input_shape,
                             filter_count=self.filter_count,
                             filter_size=self.filter_size,
                             action_count=self.action_count,
                             entropy_coefficient=self.entropy_coefficient,
                             learning_rate=self.learning_rate)
        return network

    def build(self):
        self._build_model()
        self._build_graph()

    def _build_model(self):
        with tf.variable_scope(self.name):
            input_layer = Input(shape=self.input_shape)
            cnn_input_layer = Conv2D(input_shape=self.input_shape,
                                     filters=self.filter_count,
                                     kernel_size=self.filter_size,
                                     padding='same',
                                     activation='relu',
                                     name='cnn_input')(input_layer)
            prev_layer = cnn_input_layer
            # TODO: adjust cnn layer count.
            cnn_layer_count = 0
            for i in range(cnn_layer_count):
                hidden_layer = Conv2D(filters=self.filter_count,
                                      kernel_size=self.filter_size,
                                      padding='same',
                                      activation='relu',
                                      name='conv{}'.format(i))(prev_layer)
                prev_layer = hidden_layer

            flatten_layer = Flatten()(prev_layer)

            output_policy_layer = Dense(units=self.action_count, activation='softmax')(flatten_layer)
            output_value_layer = Dense(1, activation='linear')(flatten_layer)

            model = Model(input=[input_layer], outputs=[output_policy_layer, output_value_layer])

            # Since this model will be not evaluated in a3c algorithm, expressly do it to be available vars.
            model._make_predict_function()

            self.model = model

    def _build_graph(self):
        with tf.name_scope(self.name):
            input_shape = (None,) + self.input_shape
            self.input_state_ph = tf.placeholder(tf.float32, shape=input_shape)
            self.output_policy_ph = tf.placeholder(tf.float32, shape=(None, self.action_count))
            self.output_state_value_ph = tf.placeholder(tf.float32, shape=(None, 1))

            policy, value = self.model(self.input_state_ph)

            log_pi = tf.log(tf.clip_by_value(policy, clip_value_min=1e-10, clip_value_max=1.0))
            entropy = -tf.reduce_sum(tf.multiply(policy, log_pi))

            log_pi_a_s = tf.reduce_sum(
                tf.multiply(log_pi, self.output_policy_ph), reduction_indices=1, keep_dims=True)

            advantage = self.output_state_value_ph - value

            policy_loss = -(tf.reduce_sum(log_pi_a_s * tf.stop_gradient(advantage)) + entropy * .01)
            value_loss = tf.nn.l2_loss(advantage)
            total_loss = policy_loss + value_loss

            self.get_trainable_variables_op = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope=self.name)

            gradients = tf.gradients(total_loss, self.get_trainable_variables_op)
            # TODO: adjust gradients clip value
            self.get_gradients_op = [tf.clip_by_value(grad, -40, 40) for grad in gradients]

            self.get_optimizer_op = tf.train.AdamOptimizer(self.learning_rate)

