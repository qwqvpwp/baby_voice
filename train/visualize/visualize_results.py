# -*- coding: utf-8 -*-
"""
模型评估结果可视化
生成混淆矩阵图、准确率对比图、各类别指标图
"""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import numpy as np
import json
import tensorflow as tf
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report
import matplotlib
matplotlib.use("Agg")
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
    classes = label_cfg["classes"]
    
    X_all = np.concatenate([data["X_train"], data["X_val"], data["X_test"]])
    y_all = np.concatenate([data["y_train"], data["y_val"], data["y_test"]])
    
    X_train, X_test, y_train, y_test = train_test_split(
        X_all, y_all, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_all
    )
    
    return X_test, y_test, classes


def evaluate_model(model_path, model_name, X_test, y_test, classes):
    """评估模型并返回预测结果"""
    if 'transformer' in model_path.lower():
        model = tf.keras.models.load_model(
            model_path, compile=False,
            custom_objects={"PositionalEncoding": PositionalEncoding}
        )
    else:
        model = tf.keras.models.load_model(model_path, compile=False)
    
    y_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)
    accuracy = np.mean(y_pred == y_test)
    
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=classes, output_dict=True)
    
    return accuracy, cm, report, y_pred


def plot_confusion_matrix(cm, classes, model_name, save_path):
    """绘制混淆矩阵热图"""
    plt.figure(figsize=(10, 8))
    ax = plt.gca()
    im = ax.imshow(cm, interpolation='nearest', cmap='Blues')
    
    plt.title(f'{model_name} Confusion Matrix', fontsize=16, pad=20)
    plt.xlabel('Predicted Label', fontsize=14)
    plt.ylabel('True Label', fontsize=14)
    
    tick_marks = np.arange(len(classes))
    ax.set_xticks(tick_marks)
    ax.set_xticklabels(classes, fontsize=11, rotation=45, ha='right')
    ax.set_yticks(tick_marks)
    ax.set_yticklabels(classes, fontsize=11)
    
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], 'd'),
                    ha='center', va='center', fontsize=12)
    
    plt.colorbar(im)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  已保存: {os.path.basename(save_path)}")


def plot_accuracy_comparison(cnn_acc, tf_acc, save_path):
    """绘制模型准确率对比柱状图"""
    plt.figure(figsize=(8, 6))
    
    models = ['CNN-LSTM', 'Transformer']
    accuracies = [cnn_acc * 100, tf_acc * 100]
    
    bars = plt.bar(models, accuracies, color=['#4CAF50', '#2196F3'], width=0.5)
    
    for bar, acc in zip(bars, accuracies):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f'{acc:.2f}%', ha='center', fontsize=12)
    
    plt.title('Model Accuracy Comparison', fontsize=16, pad=20)
    plt.ylabel('Accuracy (%)', fontsize=14)
    plt.ylim(0, 100)
    plt.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  已保存: {os.path.basename(save_path)}")


def plot_class_metrics(cnn_report, tf_report, classes, save_path):
    """绘制各类别指标对比图（精确率、召回率、F1）"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    metrics = ['precision', 'recall', 'f1-score']
    titles = ['Precision', 'Recall', 'F1-Score']
    
    cnn_values = [[cnn_report[c][m] * 100 for c in classes] for m in metrics]
    tf_values = [[tf_report[c][m] * 100 for c in classes] for m in metrics]
    
    x = np.arange(len(classes))
    width = 0.35
    
    for i, (ax, title) in enumerate(zip(axes, titles)):
        ax.bar(x - width/2, cnn_values[i], width, label='CNN-LSTM', color='#4CAF50')
        ax.bar(x + width/2, tf_values[i], width, label='Transformer', color='#2196F3')
        
        ax.set_title(title, fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(classes, rotation=45, ha='right', fontsize=10)
        ax.set_ylim(0, 100)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
    
    fig.suptitle('Per-Class Metrics Comparison', fontsize=16, y=1.02)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  已保存: {os.path.basename(save_path)}")


def plot_class_accuracy(cnn_cm, tf_cm, classes, save_path):
    """绘制各类别准确率对比图"""
    plt.figure(figsize=(10, 6))
    
    cnn_accs = [cnn_cm[i, i] / cnn_cm[i].sum() * 100 if cnn_cm[i].sum() > 0 else 0 
                for i in range(len(classes))]
    tf_accs = [tf_cm[i, i] / tf_cm[i].sum() * 100 if tf_cm[i].sum() > 0 else 0 
               for i in range(len(classes))]
    
    x = np.arange(len(classes))
    width = 0.35
    
    bars1 = plt.bar(x - width/2, cnn_accs, width, label='CNN-LSTM', color='#4CAF50')
    bars2 = plt.bar(x + width/2, tf_accs, width, label='Transformer', color='#2196F3')
    
    for bars, accs in zip([bars1, bars2], [cnn_accs, tf_accs]):
        for bar, acc in zip(bars, accs):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                     f'{acc:.1f}%', ha='center', fontsize=9)
    
    plt.title('Per-Class Accuracy Comparison', fontsize=16, pad=20)
    plt.xlabel('Class', fontsize=14)
    plt.ylabel('Accuracy (%)', fontsize=14)
    plt.xticks(x, classes, rotation=45, ha='right')
    plt.ylim(0, 110)
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  已保存: {os.path.basename(save_path)}")


def plot_normalized_confusion_matrix(cm, classes, model_name, save_path):
    """绘制归一化混淆矩阵（按行归一化）"""
    plt.figure(figsize=(10, 8))
    
    cm_norm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis] * 100
    
    ax = plt.gca()
    im = ax.imshow(cm_norm, interpolation='nearest', cmap='Blues', vmin=0, vmax=100)
    
    plt.title(f'{model_name} Normalized Confusion Matrix (%)', fontsize=16, pad=20)
    plt.xlabel('Predicted Label', fontsize=14)
    plt.ylabel('True Label', fontsize=14)
    
    tick_marks = np.arange(len(classes))
    ax.set_xticks(tick_marks)
    ax.set_xticklabels(classes, fontsize=11, rotation=45, ha='right')
    ax.set_yticks(tick_marks)
    ax.set_yticklabels(classes, fontsize=11)
    
    for i in range(cm_norm.shape[0]):
        for j in range(cm_norm.shape[1]):
            ax.text(j, i, f'{cm_norm[i, j]:.1f}%',
                    ha='center', va='center', fontsize=10)
    
    plt.colorbar(im, label='Percentage (%)')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  已保存: {os.path.basename(save_path)}")


def main():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    
    X_test, y_test, classes = load_data()
    
    print("\n" + "="*70)
    print("模型评估结果可视化")
    print("="*70)
    
    # 评估两个模型
    cnn_acc, cnn_cm, cnn_report, _ = evaluate_model(
        os.path.join(MODELS_DIR, 'cnn_lstm_best.h5'), 'CNN-LSTM', X_test, y_test, classes
    )
    
    tf_acc, tf_cm, tf_report, _ = evaluate_model(
        os.path.join(MODELS_DIR, 'transformer_best.h5'), 'Transformer', X_test, y_test, classes
    )
    
    print(f"\nCNN-LSTM   测试准确率: {cnn_acc*100:.2f}%")
    print(f"Transformer 测试准确率: {tf_acc*100:.2f}%")
    
    # 生成可视化图表
    print("\n" + "-"*70)
    print("生成可视化图表...")
    print("-"*70)
    
    # 1. 混淆矩阵图
    plot_confusion_matrix(cnn_cm, classes, 'CNN-LSTM', 
                          os.path.join(PLOTS_DIR, 'cnn_lstm_confusion_matrix.png'))
    plot_confusion_matrix(tf_cm, classes, 'Transformer', 
                          os.path.join(PLOTS_DIR, 'transformer_confusion_matrix.png'))
    
    # 2. 归一化混淆矩阵图
    plot_normalized_confusion_matrix(cnn_cm, classes, 'CNN-LSTM', 
                                     os.path.join(PLOTS_DIR, 'cnn_lstm_confusion_matrix_norm.png'))
    plot_normalized_confusion_matrix(tf_cm, classes, 'Transformer', 
                                     os.path.join(PLOTS_DIR, 'transformer_confusion_matrix_norm.png'))
    
    # 3. 准确率对比图
    plot_accuracy_comparison(cnn_acc, tf_acc, 
                             os.path.join(PLOTS_DIR, 'accuracy_comparison.png'))
    
    # 4. 各类别准确率对比图
    plot_class_accuracy(cnn_cm, tf_cm, classes, 
                        os.path.join(PLOTS_DIR, 'class_accuracy_comparison.png'))
    
    # 5. 各类别指标对比图（精确率、召回率、F1）
    plot_class_metrics(cnn_report, tf_report, classes, 
                       os.path.join(PLOTS_DIR, 'class_metrics_comparison.png'))
    
    print("\n" + "="*70)
    print(f"所有图表已保存到 {PLOTS_DIR}/ 目录")
    print("="*70)
    
    # 保存评估数据
    eval_data = {
        "cnn_lstm": {
            "accuracy": f"{cnn_acc*100:.2f}%",
            "confusion_matrix": cnn_cm.tolist(),
        },
        "transformer": {
            "accuracy": f"{tf_acc*100:.2f}%",
            "confusion_matrix": tf_cm.tolist(),
        },
        "classes": classes
    }
    
    with open(os.path.join(PLOTS_DIR, 'evaluation_data.json'), 'w', encoding='utf-8') as f:
        json.dump(eval_data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()