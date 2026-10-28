# -*- coding: utf-8 -*-
"""CNN-LSTM 模型训练脚本"""
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

# === 构建 CNN-LSTM 模型 ===
inp = layers.Input((40, 128, 1))

# CNN 特征提取
x = layers.Conv2D(32, 3, padding='same', activation='relu',
                  kernel_regularizer=regularizers.l2(1e-4))(inp)
x = layers.BatchNormalization()(x)
x = layers.MaxPooling2D((2, 2))(x)
x = layers.Dropout(0.3)(x)

x = layers.Conv2D(64, 3, padding='same', activation='relu',
                  kernel_regularizer=regularizers.l2(1e-4))(x)
x = layers.BatchNormalization()(x)
x = layers.MaxPooling2D((2, 2))(x)
x = layers.Dropout(0.3)(x)

x = layers.Conv2D(128, 3, padding='same', activation='relu',
                  kernel_regularizer=regularizers.l2(1e-4))(x)
x = layers.BatchNormalization()(x)
x = layers.MaxPooling2D((2, 1))(x)
x = layers.Dropout(0.3)(x)

# 转为时序格式 (batch, time, features)
x = layers.Reshape((x.shape[1] * x.shape[2], x.shape[3]))(x)

# LSTM 时序建模
x = layers.LSTM(128, return_sequences=True, dropout=0.3)(x)
x = layers.LSTM(64, return_sequences=False, dropout=0.3)(x)

# 分类头
x = layers.Dense(128, activation='relu',
                 kernel_regularizer=regularizers.l2(1e-4))(x)
x = layers.Dropout(0.5)(x)
x = layers.Dense(64, activation='relu',
                 kernel_regularizer=regularizers.l2(1e-4))(x)
x = layers.Dropout(0.5)(x)

out = layers.Dense(num_classes, activation='softmax')(x)
model = Model(inp, out, name='CNN_LSTM')
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
    callbacks.ModelCheckpoint('models_output/cnn_lstm_best.h5', 'val_accuracy',
                              save_best_only=True, verbose=1)
]

print('\n开始训练 CNN-LSTM...')
hist = model.fit(
    X_train, y_train_oh,
    batch_size=32, epochs=80,
    validation_data=(X_val, y_val_oh),
    callbacks=cb, verbose=1
)

# 测试
loss, acc = model.evaluate(X_test, y_test_oh, verbose=0)
print(f'\n===== CNN-LSTM 测试准确率: {acc:.4f} ({acc*100:.2f}%) =====')

# 保存
model.save('models_output/cnn_lstm_final.h5')
print('模型已保存: models_output/cnn_lstm_final.h5')

# TFLite 导出
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()
with open('models_output/cnn_lstm.tflite', 'wb') as f:
    f.write(tflite_model)
print('TFLite 已导出: models_output/cnn_lstm.tflite')