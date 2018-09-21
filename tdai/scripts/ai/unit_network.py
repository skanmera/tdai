# -*- coding: utf-8 -*-


__author__ = "skanmera"
__copyright__ = "Copyright 2018, skanmera"


import tensorflow as tf
from keras.models import Model
from keras.layers import Input, Dense, Conv2D, Flatten, concatenate


class UnitNetwork(object):

    def __init__(self,
                 name,
                 input_state_shape,
                 input_location_shape,
                 input_unit_shape,
                 input_action_shape,
                 filter_count=1,
                 filter_size=(3, 3),
                 entropy_coefficient=.01,
                 learning_rate=5e-3):
        self.name = name
        self.input_state_shape = input_state_shape
        self.input_location_shape = input_location_shape
        self.input_unit_shape = input_unit_shape
        self.input_action_shape = input_action_shape
        self.filter_count = filter_count
        self.filter_size = filter_size
        self.entropy_coefficient = entropy_coefficient
        self.learning_rate = learning_rate
        self.model = None
        self.input_state_ph = None
        self.input_location_ph = None
        self.input_unit_ph = None
        self.input_action_ph = None
        self.output_value_ph = None
        self.get_trainable_variables_op = None
        self.get_gradients_op = None
        self.get_total_loss_op = None
        self.get_optimizer_op = None
        self.apply_gradients_op = None

    def build(self):
        self._build_model()
        self._build_graph()

    def clone(self, name):
        return UnitNetwork(name=name,
                           input_state_shape=self.input_state_shape,
                           input_location_shape=self.input_location_shape,
                           input_unit_shape=self.input_unit_shape,
                           input_action_shape=self.input_action_shape,
                           filter_count=self.filter_count,
                           filter_size=self.filter_size,
                           entropy_coefficient=self.entropy_coefficient,
                           learning_rate=self.learning_rate)

    def _build_model(self):
        with tf.variable_scope(self.name):
            # -----------------state-----------------
            state_input_layer = Input(shape=self.input_state_shape)
            state_cnn_input_layer = Conv2D(input_shape=self.input_state_shape,
                                           filters=self.filter_count,
                                           kernel_size=self.filter_size,
                                           padding='same',
                                           activation='relu',
                                           name='state_cnn_input')(state_input_layer)
            prev_layer = state_cnn_input_layer
            # TODO: find best count.
            convolution_count = 0
            for i in range(convolution_count):
                hidden_layer = Conv2D(filters=self.filter_count,
                                      kernel_size=self.filter_size,
                                      padding='same',
                                      activation='relu',
                                      name='conv{}'.format(i))(prev_layer)
                prev_layer = hidden_layer

            state_flatten_layer = Flatten()(prev_layer)

            # -----------------location-----------------
            location_input_layer = Input(shape=self.input_location_shape)
            location_cnn_input_layer = Conv2D(input_shape=self.input_location_shape,
                                              filters=self.filter_count,
                                              kernel_size=self.filter_size,
                                              padding='same',
                                              activation='relu',
                                              name='location_cnn_input')(location_input_layer)
            prev_layer = location_cnn_input_layer
            convolution_count = 0
            for i in range(convolution_count):
                hidden_layer = Conv2D(filters=self.filter_count,
                                      kernel_size=self.filter_size,
                                      padding='same',
                                      activation='relu',
                                      name='conv{}'.format(i))(prev_layer)
                prev_layer = hidden_layer

            location_flatten_layer = Flatten()(prev_layer)

            # -----------------unit-----------------
            unit_input_layer = Input(shape=self.input_unit_shape)
            unit_flatten_layer = Flatten()(unit_input_layer)

            # -----------------action-----------------
            action_input_layer = Input(shape=self.input_action_shape)
            action_flatten_layer = Flatten()(action_input_layer)

            # -----------------merge-----------------
            merged_layer = concatenate([state_flatten_layer,
                                        location_flatten_layer,
                                        unit_flatten_layer,
                                        action_flatten_layer])

            # -----------------output-----------------
            output_value = Dense(1, activation='linear')(merged_layer)

            model = Model(input=[state_input_layer,
                                 location_input_layer,
                                 unit_input_layer,
                                 action_input_layer],
                          outputs=[output_value])

            model._make_predict_function()

            self.model = model

    def _build_graph(self):
        with tf.name_scope(self.name):
            input_state_shape = (None,) + self.input_state_shape
            self.input_state_ph = tf.placeholder(tf.float32, shape=input_state_shape)
            input_location_shape = (None,) + self.input_location_shape
            self.input_location_ph = tf.placeholder(tf.float32, shape=input_location_shape)
            input_unit_shape = (None,) + self.input_unit_shape
            self.input_unit_ph = tf.placeholder(tf.float32, shape=input_unit_shape)
            input_action_shape = (None,) + self.input_action_shape
            self.input_action_ph = tf.placeholder(tf.float32, shape=input_action_shape)
            self.output_value_ph = tf.placeholder(tf.float32, shape=(None, 1))

            value = self.model([self.input_state_ph,
                                self.input_location_ph,
                                self.input_unit_ph,
                                self.input_action_ph])

            value_loss = tf.nn.l2_loss(self.output_value_ph - value)

            self.get_trainable_variables_op = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope=self.name)

            gradients = tf.gradients(value_loss, self.get_trainable_variables_op)
            self.get_gradients_op = [tf.clip_by_value(grad, -40, 40) for grad in gradients]

            self.get_optimizer_op = tf.train.AdamOptimizer(self.learning_rate)
