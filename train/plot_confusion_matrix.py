# -*- coding: utf-8 -*-
"""
生成混淆矩阵可视化图表
"""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import numpy as np
import json
import tensorflow as tf
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix
import matplotlib
matplotlib.use("Agg")  # 非交互式后端
import matplotlib.pyplot as plt

# ============ 配置参数 ============
PROCESSED_DIR = "processed_data"
MODELS_DIR = "models_output"
PLOTS_DIR = "plots"
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
    mapping = label_cfg['mapping']
    
    X_all = np.concatenate([data["X_train"], data["X_val"], data["X_test"]])
    y_all = np.concatenate([data["y_train"], data["y_val"], data["y_test"]])
    
    X_train, X_test, y_train, y_test = train_test_split(
        X_all, y_all, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_all
    )
    
    return X_test, y_test, classes, mapping


def plot_confusion_matrix(cm, classes, mapping, model_name, save_path):
    """绘制混淆矩阵热图（使用纯 matplotlib）"""
    plt.figure(figsize=(10, 8))
    
    # 绘制热图
    ax = plt.gca()
    im = ax.imshow(cm, interpolation='nearest', cmap='Blues')
    
    # 设置标题和标签（使用英文避免中文乱码）
    plt.title(f'{model_name} Confusion Matrix', fontsize=16, pad=20)
    plt.xlabel('Predicted Label', fontsize=14)
    plt.ylabel('True Label', fontsize=14)
    
    # 设置刻度（使用英文类别名）
    tick_marks = np.arange(len(classes))
    ax.set_xticks(tick_marks)
    ax.set_xticklabels(classes, fontsize=11, rotation=45, ha='right')
    ax.set_yticks(tick_marks)
    ax.set_yticklabels(classes, fontsize=11)
    
    # 添加数值标注
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], 'd'),
                    ha='center', va='center', fontsize=12)
    
    # 添加颜色条
    plt.colorbar(im)
    
    # 调整布局并保存
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  混淆矩阵图已保存: {save_path}")


def evaluate_and_plot(model_path, model_name, X_test, y_test, classes, mapping, plots_dir):
    """评估模型并生成混淆矩阵图"""
    print(f"\n{'='*60}")
    print(f"  生成 {model_name} 混淆矩阵图")
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
    print(f"  测试准确率: {accuracy*100:.2f}%")
    
    cm = confusion_matrix(y_test, y_pred)
    
    save_path = os.path.join(plots_dir, f'{model_name.lower()}_confusion_matrix.png')
    plot_confusion_matrix(cm, classes, mapping, model_name, save_path)
    
    return accuracy


def main():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    
    X_test, y_test, classes, mapping = load_data()
    
    print("\n" + "="*70)
    print("生成混淆矩阵可视化图表")
    print("="*70)
    
    acc_cnn = evaluate_and_plot(
        os.path.join(MODELS_DIR, 'cnn_lstm_best.h5'), 
        'CNN-LSTM', X_test, y_test, classes, mapping, PLOTS_DIR
    )
    
    acc_tf = evaluate_and_plot(
        os.path.join(MODELS_DIR, 'transformer_best.h5'), 
        'Transformer', X_test, y_test, classes, mapping, PLOTS_DIR
    )
    
    print("\n" + "="*70)
    print("生成完成！")
    print("="*70)
    print(f"  CNN-LSTM   测试准确率: {acc_cnn*100:.2f}%")
    print(f"  Transformer 测试准确率: {acc_tf*100:.2f}%")
    print(f"  图表已保存到 {PLOTS_DIR}/ 目录")


if __name__ == "__main__":
    main()