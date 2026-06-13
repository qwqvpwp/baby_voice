# -*- coding: utf-8 -*-
"""
模型训练脚本
支持 CNN-LSTM 和 Transformer 两种模型
"""
import os
import json
import numpy as np
import pickle
import tensorflow as tf
from tensorflow.keras import optimizers, callbacks
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from models import build_model

# ============ 配置 ============
PROCESSED_DIR = "processed_data"
MODELS_DIR = "models_output"
BATCH_SIZE = 32
EPOCHS = 80
LEARNING_RATE = 0.001
PATIENCE = 15  # EarlyStopping 耐心值


def load_processed_data():
    """加载预处理后的数据"""
    data = np.load(os.path.join(PROCESSED_DIR, "dataset.npz"))
    with open(os.path.join(PROCESSED_DIR, "label_encoder.pkl"), "rb") as f:
        label_encoder = pickle.load(f)

    return (
        data["X_train"], data["y_train"],
        data["X_val"], data["y_val"],
        data["X_test"], data["y_test"],
        label_encoder
    )


def create_callbacks(model_name):
    """创建训练回调"""
    os.makedirs(MODELS_DIR, exist_ok=True)

    ckpt_path = os.path.join(MODELS_DIR, f"{model_name}_best.h5")

    return [
        callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=PATIENCE,
            restore_best_weights=True,
            verbose=1
        ),
        callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=7,
            min_lr=1e-6,
            verbose=1
        ),
        callbacks.ModelCheckpoint(
            ckpt_path,
            monitor="val_accuracy",
            save_best_only=True,
            verbose=1
        )
    ]


def plot_training_history(history, model_name):
    """绘制训练曲线"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # 损失曲线
    ax1.plot(history["loss"], label="训练损失")
    ax1.plot(history["val_loss"], label="验证损失")
    ax1.set_title(f"{model_name} - 损失曲线")
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("Loss")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 准确率曲线
    ax2.plot(history["accuracy"], label="训练准确率")
    ax2.plot(history["val_accuracy"], label="验证准确率")
    ax2.set_title(f"{model_name} - 准确率曲线")
    ax2.set_xlabel("Epoch")
    ax2.set_ylabel("Accuracy")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(MODELS_DIR, f"{model_name}_training_curve.png"), dpi=150)
    plt.close()
    print(f"  训练曲线已保存: {model_name}_training_curve.png")


def train_model(model_type="cnn_lstm"):
    """训练单个模型"""
    print("\n" + "=" * 60)
    print(f"训练模型: {model_type.upper()}")
    print("=" * 60)

    # 加载数据
    X_train, y_train, X_val, y_val, X_test, y_test, label_encoder = load_processed_data()
    num_classes = len(label_encoder.classes_)
    input_shape = X_train.shape[1:]

    print(f"  输入形状: {input_shape}")
    print(f"  类别数: {num_classes}")
    print(f"  训练集: {len(X_train)}, 验证集: {len(X_val)}, 测试集: {len(X_test)}")

    # 转换标签为 one-hot
    y_train_oh = tf.keras.utils.to_categorical(y_train, num_classes)
    y_val_oh = tf.keras.utils.to_categorical(y_val, num_classes)
    y_test_oh = tf.keras.utils.to_categorical(y_test, num_classes)

    # 构建模型
    model = build_model(model_type, input_shape, num_classes)
    model.summary()

    # 编译
    model.compile(
        optimizer=optimizers.Adam(learning_rate=LEARNING_RATE),
        loss="categorical_crossentropy",
        metrics=["accuracy"]
    )

    # 训练
    history = model.fit(
        X_train, y_train_oh,
        batch_size=BATCH_SIZE,
        epochs=EPOCHS,
        validation_data=(X_val, y_val_oh),
        callbacks=create_callbacks(model_type),
        verbose=1
    )

    # 绘制训练曲线
    plot_training_history(history.history, model_type)

    # 评估
    print("\n" + "-" * 40)
    print("测试集评估")
    print("-" * 40)
    test_loss, test_acc = model.evaluate(X_test, y_test_oh, verbose=0)
    print(f"  {model_type} 测试准确率: {test_acc:.4f} ({test_acc * 100:.2f}%)")
    print(f"  测试损失: {test_loss:.4f}")

    # 保存最终模型
    final_path = os.path.join(MODELS_DIR, f"{model_type}_final.h5")
    model.save(final_path)
    print(f"  最终模型已保存: {final_path}")

    # 导出 TFLite（用于移动端/小程序）
    print("\n  正在导出 TFLite 模型...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    tflite_path = os.path.join(MODELS_DIR, f"{model_type}.tflite")
    with open(tflite_path, "wb") as f:
        f.write(tflite_model)
    print(f"  TFLite 模型已保存: {tflite_path}")

    return test_acc, history.history


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)

    results = {}

    # 训练 CNN-LSTM
    acc_cnnlstm, hist_cnnlstm = train_model("cnn_lstm")
    results["cnn_lstm"] = {"test_accuracy": float(acc_cnnlstm)}

    # 训练 Transformer
    acc_trans, hist_trans = train_model("transformer")
    results["transformer"] = {"test_accuracy": float(acc_trans)}

    # 保存结果摘要
    summary = {
        "models": results,
        "best_model": "cnn_lstm" if acc_cnnlstm >= acc_trans else "transformer",
        "cnn_lstm_accuracy": f"{acc_cnnlstm * 100:.2f}%",
        "transformer_accuracy": f"{acc_trans * 100:.2f}%",
    }
    with open(os.path.join(MODELS_DIR, "training_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("训练完成！结果摘要")
    print("=" * 60)
    print(f"  CNN-LSTM  测试准确率: {acc_cnnlstm * 100:.2f}%")
    print(f"  Transformer 测试准确率: {acc_trans * 100:.2f}%")
    print(f"  最佳模型: {summary['best_model']}")


if __name__ == "__main__":
    main()