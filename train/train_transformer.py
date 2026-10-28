# -*- coding: utf-8 -*-
"""Transformer 模型训练脚本"""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import numpy as np
import json
import tensorflow as tf
from tensorflow.keras import layers, Model, regularizers, callbacks, optimizers

# 加载数据
data = np.load('processed_data/dataset.npz')
X_train, y_train = data['X_train'], data['y_train']
X_val, y_val = data['X_val'], data['y_val']
X_test, y_test = data['X_test'], data['y_test']

with open('processed_data/label_config.json', 'r', encoding='utf-8') as f:
    label_cfg = json.load(f)
num_classes = len(label_cfg['classes'])
print(f'类别数: {num_classes}, 类别: {label_cfg["classes"]}')
print(f'训练集: {X_train.shape}, 验证集: {X_val.shape}, 测试集: {X_test.shape}')

# One-hot
y_train_oh = tf.keras.utils.to_categorical(y_train, num_classes)
y_val_oh = tf.keras.utils.to_categorical(y_val, num_classes)
y_test_oh = tf.keras.utils.to_categorical(y_test, num_classes)

# ========== 位置编码层 ==========
class PositionalEncoding(layers.Layer):
    def __init__(self, d_model, max_len=200, **kwargs):
        super().__init__(**kwargs)
        self.d_model = d_model
        self.max_len = max_len

    def call(self, x):
        batch_size = tf.shape(x)[0]
        seq_len = tf.shape(x)[1]
        position = tf.cast(tf.range(seq_len)[:, tf.newaxis], tf.float32)
        div_term = tf.exp(tf.range(0, self.d_model, 2, dtype=tf.float32) *
                          -(tf.math.log(10000.0) / tf.cast(self.d_model, tf.float32)))
        pe = tf.TensorArray(tf.float32, size=seq_len)
        for pos in range(seq_len):
            vals = tf.zeros((self.d_model,))
            for i in range(0, self.d_model, 2):
                idx = tf.constant(i)
                sin_val = tf.sin(tf.cast(pos, tf.float32) * div_term[i // 2])
                cos_val = tf.cos(tf.cast(pos, tf.float32) * div_term[i // 2])
                vals = tf.tensor_scatter_nd_update(vals, [[idx]], [sin_val])
                if i + 1 < self.d_model:
                    vals = tf.tensor_scatter_nd_update(vals, [[idx + 1]], [cos_val])
            pe = pe.write(pos, vals)
        pe = pe.stack()
        return x + pe[tf.newaxis, :seq_len, :]


# ========== Transformer Encoder 块 ==========
def transformer_block(x, d_model, num_heads, ff_dim, dropout=0.3):
    # Multi-Head Self-Attention
    attn = layers.MultiHeadAttention(
        num_heads=num_heads, key_dim=d_model // num_heads, dropout=dropout
    )(x, x)
    attn = layers.Dropout(dropout)(attn)
    x1 = layers.LayerNormalization(epsilon=1e-6)(x + attn)

    # Feed-Forward
    ff = layers.Dense(ff_dim, activation='relu')(x1)
    ff = layers.Dense(d_model)(ff)
    ff = layers.Dropout(dropout)(ff)
    x2 = layers.LayerNormalization(epsilon=1e-6)(x1 + ff)
    return x2


# ========== 构建 Transformer 模型 ==========
D_MODEL = 64
NUM_HEADS = 4
NUM_BLOCKS = 3
FF_DIM = 256
DROPOUT = 0.3

inp = layers.Input((40, 128, 1))

# CNN 降维
x = layers.Conv2D(32, (3, 3), padding='same', activation='relu')(inp)
x = layers.BatchNormalization()(x)
x = layers.MaxPooling2D((2, 2))(x)
x = layers.Dropout(0.2)(x)

x = layers.Conv2D(D_MODEL, (3, 3), padding='same', activation='relu')(x)
x = layers.BatchNormalization()(x)
x = layers.MaxPooling2D((2, 2))(x)
x = layers.Dropout(0.2)(x)

# (B, H, W, C) -> (B, H*W, C) -> project to D_MODEL
x = layers.Reshape((x.shape[1] * x.shape[2], x.shape[3]))(x)
x = layers.Dense(D_MODEL, activation='relu')(x)

# 位置编码
x = PositionalEncoding(D_MODEL)(x)

# Transformer Encoder blocks
for i in range(NUM_BLOCKS):
    x = transformer_block(x, D_MODEL, NUM_HEADS, FF_DIM, DROPOUT)

# 分类头
x = layers.GlobalAveragePooling1D()(x)
x = layers.Dropout(0.5)(x)
x = layers.Dense(128, activation='relu',
                 kernel_regularizer=regularizers.l2(1e-4))(x)
x = layers.Dropout(0.5)(x)

out = layers.Dense(num_classes, activation='softmax')(x)
model = Model(inp, out, name='Transformer')
model.summary()

# 编译与训练
model.compile(
    optimizer=optimizers.Adam(0.001),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

os.makedirs('models_output', exist_ok=True)
cb = [
    callbacks.EarlyStopping('val_accuracy', patience=15,
                            restore_best_weights=True, verbose=1),
    callbacks.ReduceLROnPlateau('val_loss', factor=0.5, patience=7,
                                min_lr=1e-6, verbose=1),
    callbacks.ModelCheckpoint('models_output/transformer_best.h5', 'val_accuracy',
                              save_best_only=True, verbose=1)
]

print('\n开始训练 Transformer...')
hist = model.fit(
    X_train, y_train_oh,
    batch_size=32, epochs=80,
    validation_data=(X_val, y_val_oh),
    callbacks=cb, verbose=1
)

# 测试
loss, acc = model.evaluate(X_test, y_test_oh, verbose=0)
print(f'\n===== Transformer 测试准确率: {acc:.4f} ({acc*100:.2f}%) =====')

# 保存
model.save('models_output/transformer_final.h5')
print('模型已保存: models_output/transformer_final.h5')

# TFLite 导出
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()
with open('models_output/transformer.tflite', 'wb') as f:
    f.write(tflite_model)
print('TFLite 已导出: models_output/transformer.tflite')