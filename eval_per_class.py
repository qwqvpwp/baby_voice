# -*- coding: utf-8 -*-
"""按类别评估两个模型的准确率、精确率、召回率、F1"""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import numpy as np
import json
import tensorflow as tf
from tensorflow.keras import layers
from sklearn.metrics import classification_report, confusion_matrix


# 注册自定义层 (Trainer 中定义的 PositionalEncoding)
@tf.keras.utils.register_keras_serializable()
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

    def get_config(self):
        config = super().get_config()
        config.update({"d_model": self.d_model, "max_len": self.max_len})
        return config

# 加载数据
data = np.load('processed_data/dataset.npz')
X_test, y_test = data['X_test'], data['y_test']

with open('processed_data/label_config.json', 'r', encoding='utf-8') as f:
    label_cfg = json.load(f)
classes = label_cfg['classes']
id_to_class = label_cfg['id_to_class']
label_mapping = label_cfg['mapping']

y_test_oh = tf.keras.utils.to_categorical(y_test, len(classes))

def evaluate_model(model_path, name):
    print(f"\n{'='*60}")
    print(f"  {name} 模型 — 各类别准确率")
    print(f"{'='*60}")

    model = tf.keras.models.load_model(
        model_path, compile=False,
        custom_objects={"PositionalEncoding": PositionalEncoding}
    )
    y_pred_prob = model.predict(X_test, verbose=0)
    y_pred = np.argmax(y_pred_prob, axis=1)

    # 各类别准确率 (per-class accuracy = recall)
    print(f"\n{'类别':<16} {'中文':<10} {'样本数':>6} {'正确数':>6} {'准确率':>8}")
    print("-" * 58)
    for i, cls in enumerate(classes):
        mask = y_test == i
        total = np.sum(mask)
        correct = np.sum((y_pred == i) & mask) if total > 0 else 0
        acc = correct / total * 100 if total > 0 else 0
        cn = label_mapping.get(cls, cls)
        print(f"  {cls:<14} {cn:<10} {total:>6} {correct:>6} {acc:>7.2f}%")

    # 总体
    total_correct = np.sum(y_pred == y_test)
    total_samples = len(y_test)
    print("-" * 58)
    print(f"  {'总体':<14} {'':10} {total_samples:>6} {total_correct:>6} {total_correct/total_samples*100:>7.2f}%")

    # 混淆矩阵
    cm = confusion_matrix(y_test, y_pred)
    print(f"\n混淆矩阵 (行=真实, 列=预测):")
    header = "        " + "".join(f"{cls[:6]:>8}" for cls in classes)
    print(header)
    for i, cls in enumerate(classes):
        row = f"  {cls[:6]:>6}" + "".join(f"{cm[i][j]:>8}" for j in range(len(classes)))
        print(row)

    # sklearn 完整报告
    print(f"\nsklearn 分类报告:")
    print(classification_report(
        y_test, y_pred,
        target_names=[f"{cls}({label_mapping.get(cls, cls)})" for cls in classes],
        digits=3
    ))

    return total_correct / total_samples

# 评估两个模型
acc_cnn = evaluate_model('models_output/cnn_lstm_best.h5', 'CNN-LSTM')
acc_tf  = evaluate_model('models_output/transformer_best.h5', 'Transformer')

print(f"\n{'='*60}")
print(f"  对比总结")
print(f"{'='*60}")
print(f"  CNN-LSTM   测试准确率: {acc_cnn*100:.2f}%")
print(f"  Transformer 测试准确率: {acc_tf*100:.2f}%")