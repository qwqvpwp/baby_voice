# -*- coding: utf-8 -*-
"""
语音分类模型定义
- CNN-LSTM 混合模型
- Transformer（Self-Attention）模型
"""
import tensorflow as tf
from tensorflow.keras import layers, Model, regularizers


def cnn_lstm_model(input_shape=(40, 128, 1), num_classes=7):
    """
    CNN-LSTM 混合模型
    结构：3 层 CNN → BatchNorm → MaxPooling → LSTM → Dense → Dropout → Output
    """
    inputs = layers.Input(shape=input_shape, name="mfcc_input")

    # === CNN 特征提取 ===
    x = layers.Conv2D(32, (3, 3), padding="same", activation="relu",
                      kernel_regularizer=regularizers.l2(1e-4))(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.3)(x)

    x = layers.Conv2D(64, (3, 3), padding="same", activation="relu",
                      kernel_regularizer=regularizers.l2(1e-4))(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.3)(x)

    x = layers.Conv2D(128, (3, 3), padding="same", activation="relu",
                      kernel_regularizer=regularizers.l2(1e-4))(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 1))(x)  # 仅在频率维度池化
    x = layers.Dropout(0.3)(x)

    # === 转换为时序格式 (batch, time, features) ===
    x = layers.Reshape((x.shape[1] * x.shape[2], x.shape[3]))(x)

    # === LSTM 时序建模 ===
    x = layers.LSTM(128, return_sequences=True, dropout=0.3)(x)
    x = layers.LSTM(64, return_sequences=False, dropout=0.3)(x)

    # === 分类头 ===
    x = layers.Dense(128, activation="relu",
                     kernel_regularizer=regularizers.l2(1e-4))(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(64, activation="relu",
                     kernel_regularizer=regularizers.l2(1e-4))(x)
    x = layers.Dropout(0.5)(x)

    outputs = layers.Dense(num_classes, activation="softmax", name="output")(x)

    model = Model(inputs=inputs, outputs=outputs, name="CNN_LSTM")
    return model


# ============ Transformer 模型 ============

class PositionalEncoding(layers.Layer):
    """位置编码层"""
    def __init__(self, d_model, max_len=200):
        super().__init__()
        self.d_model = d_model
        self.max_len = max_len

    def build(self, input_shape):
        position = tf.range(self.max_len, dtype=tf.float32)[:, tf.newaxis]
        div_term = tf.exp(tf.range(0, self.d_model, 2, dtype=tf.float32) *
                          -(tf.math.log(10000.0) / self.d_model))
        pe = tf.Variable(tf.zeros((self.max_len, self.d_model)), trainable=False)
        pe_updated = tf.tensor_scatter_nd_update(
            pe,
            tf.stack([tf.range(self.max_len), tf.repeat(0, self.max_len)], axis=1),
            tf.sin(position[:, 0] * div_term[0:1])
        )
        self.pe = pe
        super().build(input_shape)

    def call(self, x):
        # x: (batch, seq_len, d_model)
        seq_len = tf.shape(x)[1]
        # 使用 sin/cos 交替
        position = tf.cast(tf.range(seq_len)[:, tf.newaxis], tf.float32)
        div_term = tf.exp(tf.range(0, self.d_model, 2, dtype=tf.float32) *
                          -(tf.math.log(10000.0) / tf.cast(self.d_model, tf.float32)))
        pe_sin = tf.sin(position * div_term)
        pe_cos = tf.cos(position * div_term)
        pe_vals = tf.reshape(tf.stack([pe_sin, pe_cos], axis=-1), [seq_len, self.d_model])
        return x + pe_vals[tf.newaxis, :seq_len, :self.d_model]


def transformer_encoder(inputs, d_model, num_heads, ff_dim, dropout=0.3):
    """单个 Transformer Encoder 块"""
    # Multi-Head Self-Attention
    attn = layers.MultiHeadAttention(
        num_heads=num_heads, key_dim=d_model // num_heads, dropout=dropout
    )(inputs, inputs)
    attn = layers.Dropout(dropout)(attn)
    x1 = layers.LayerNormalization(epsilon=1e-6)(inputs + attn)

    # Feed-Forward Network
    ff = layers.Dense(ff_dim, activation="relu")(x1)
    ff = layers.Dense(d_model)(ff)
    ff = layers.Dropout(dropout)(ff)
    x2 = layers.LayerNormalization(epsilon=1e-6)(x1 + ff)

    return x2


def transformer_model(input_shape=(40, 128, 1), num_classes=7,
                      d_model=64, num_heads=4, num_blocks=3, ff_dim=256, dropout=0.3):
    """
    Transformer（Self-Attention）模型
    结构：CNN 降维 → Positional Encoding → Transformer Encoder × N → GlobalPooling → Dense → Output
    """
    inputs = layers.Input(shape=input_shape, name="mfcc_input")

    # === CNN 降维 ===
    x = layers.Conv2D(32, (3, 3), padding="same", activation="relu")(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.2)(x)

    x = layers.Conv2D(d_model, (3, 3), padding="same", activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.2)(x)

    # (batch, freq, time, d_model) → (batch, time, freq*d_model) → project to d_model
    x = layers.Reshape((x.shape[1] * x.shape[2], x.shape[3]))(x)
    x = layers.Dense(d_model, activation="relu")(x)

    # === Positional Encoding ===
    x = PositionalEncoding(d_model)(x)

    # === Transformer Encoder Blocks ===
    for i in range(num_blocks):
        x = transformer_encoder(x, d_model, num_heads, ff_dim, dropout)

    # === Global Pooling + 分类头 ===
    x = layers.GlobalAveragePooling1D()(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(128, activation="relu",
                     kernel_regularizer=regularizers.l2(1e-4))(x)
    x = layers.Dropout(0.5)(x)

    outputs = layers.Dense(num_classes, activation="softmax", name="output")(x)

    model = Model(inputs=inputs, outputs=outputs, name="Transformer")
    return model


def build_model(model_type="cnn_lstm", input_shape=(40, 128, 1), num_classes=7):
    """统一模型构建接口"""
    if model_type == "cnn_lstm":
        return cnn_lstm_model(input_shape, num_classes)
    elif model_type == "transformer":
        return transformer_model(input_shape, num_classes)
    else:
        raise ValueError(f"不支持的模型类型: {model_type}")