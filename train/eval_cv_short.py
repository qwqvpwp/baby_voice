# -*- coding: utf-8 -*-
"""
快速评估脚本：8:2 划分 + 混淆矩阵输出
"""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import numpy as np
import json
import tensorflow as tf
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report

# ============ 配置参数 ============
PROCESSED_DIR = "processed_data"
MODELS_DIR = "models_output"
TEST_SIZE = 0.2
RANDOM_STATE = 42

# ============ 自定义层（Transformer 需要） ============
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


def load_data():
    """按 8:2 划分数据"""
    data = np.load(os.path.join(PROCESSED_DIR, "dataset.npz"))
    
    with open(os.path.join(PROCESSED_DIR, "label_config.json"), "r", encoding="utf-8") as f:
        label_cfg = json.load(f)
    classes = label_cfg['classes']
    
    X_all = np.concatenate([data["X_train"], data["X_val"], data["X_test"]])
    y_all = np.concatenate([data["y_train"], data["y_val"], data["y_test"]])
    
    print(f"总样本数: {len(X_all)}")
    print(f"类别分布: {dict(zip(classes, np.bincount(y_all)))}")
    
    X_train, X_test, y_train, y_test = train_test_split(
        X_all, y_all, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_all
    )
    
    print(f"\n8:2 划分结果:")
    print(f"  训练集: {len(X_train)} 样本 ({len(X_train)/len(X_all)*100:.1f}%)")
    print(f"  测试集: {len(X_test)} 样本 ({len(X_test)/len(X_all)*100:.1f}%)")
    
    return X_train, X_test, y_train, y_test, classes


def print_confusion_matrix(y_true, y_pred, classes):
    """打印混淆矩阵"""
    cm = confusion_matrix(y_true, y_pred)
    
    print("\n混淆矩阵 (行=真实标签, 列=预测标签):")
    header = "        " + "".join(f"{cls[:6]:>8}" for cls in classes)
    print(header)
    for i, cls in enumerate(classes):
        row = f"  {cls[:6]:>6}" + "".join(f"{cm[i][j]:>8}" for j in range(len(classes)))
        print(row)


def evaluate_model(model_path, model_name, X_test, y_test, classes):
    """评估单个模型"""
    print(f"\n{'='*60}")
    print(f"  {model_name} 模型评估")
    print(f"{'='*60}")
    
    if 'transformer' in model_path.lower():
        model = tf.keras.models.load_model(
            model_path, compile=False,
            custom_objects={"PositionalEncoding": PositionalEncoding}
        )
    else:
        model = tf.keras.models.load_model(model_path, compile=False)
    
    y_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)
    accuracy = np.mean(y_pred == y_test)
    
    print(f"测试准确率: {accuracy*100:.2f}%")
    
    print_confusion_matrix(y_test, y_pred, classes)
    
    print(f"\n分类报告:")
    print(classification_report(y_test, y_pred, target_names=classes, digits=3))
    
    return accuracy


def main():
    X_train, X_test, y_train, y_test, classes = load_data()
    
    print("\n" + "="*70)
    print("使用 8:2 划分后的测试集评估现有模型")
    print("="*70)
    
    evaluate_model(os.path.join(MODELS_DIR, 'cnn_lstm_best.h5'), 'CNN-LSTM', 
                   X_test, y_test, classes)
    evaluate_model(os.path.join(MODELS_DIR, 'transformer_best.h5'), 'Transformer', 
                   X_test, y_test, classes)


if __name__ == "__main__":
    main()