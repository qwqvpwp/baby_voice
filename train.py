# -*- coding: utf-8 -*-
"""
模型训练脚本（8:2 划分 + 5 折交叉验证）
- 支持 CNN-LSTM 和 Transformer 两种模型
- 输出交叉验证结果、混淆矩阵和分类报告
"""
import os
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras import optimizers, callbacks
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import confusion_matrix, classification_report
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
PATIENCE = 15          # EarlyStopping 耐心值
KFOLDS = 5             # 交叉验证折数
TEST_SIZE = 0.2        # 测试集比例
RANDOM_STATE = 42


def load_data():
    """加载预处理数据，按 8:2 重新划分为训练集和测试集"""
    data = np.load(os.path.join(PROCESSED_DIR, "dataset.npz"))
    with open(os.path.join(PROCESSED_DIR, "label_config.json"), "r", encoding="utf-8") as f:
        label_cfg = json.load(f)
    classes = label_cfg["classes"]

    X_all = np.concatenate([data["X_train"], data["X_val"], data["X_test"]])
    y_all = np.concatenate([data["y_train"], data["y_val"], data["y_test"]])

    print(f"\n总样本数: {len(X_all)}")
    print(f"类别分布: {dict(zip(classes, np.bincount(y_all)))}")

    X_train, X_test, y_train, y_test = train_test_split(
        X_all, y_all, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_all
    )

    print(f"8:2 划分: 训练集 {len(X_train)} / 测试集 {len(X_test)}")
    return X_train, X_test, y_train, y_test, classes


def run_cross_validation(X_train, y_train, model_type, num_classes, classes):
    """5 折分层交叉验证"""
    skf = StratifiedKFold(n_splits=KFOLDS, shuffle=True, random_state=RANDOM_STATE)
    fold_accs = []
    input_shape = X_train.shape[1:]

    print(f"\n{'='*60}")
    print(f"  {model_type.upper()} - {KFOLDS}-Fold 交叉验证")
    print(f"{'='*60}")

    for fold, (train_idx, val_idx) in enumerate(skf.split(X_train, y_train), 1):
        X_fold_train, X_fold_val = X_train[train_idx], X_train[val_idx]
        y_fold_train, y_fold_val = y_train[train_idx], y_train[val_idx]

        y_fold_train_oh = tf.keras.utils.to_categorical(y_fold_train, num_classes)
        y_fold_val_oh = tf.keras.utils.to_categorical(y_fold_val, num_classes)

        model = build_model(model_type, input_shape, num_classes)
        model.compile(
            optimizer=optimizers.Adam(LEARNING_RATE),
            loss="categorical_crossentropy",
            metrics=["accuracy"]
        )

        cb = [
            callbacks.EarlyStopping("val_accuracy", patience=PATIENCE,
                                    restore_best_weights=True, verbose=0),
            callbacks.ReduceLROnPlateau("val_loss", factor=0.5, patience=7,
                                        min_lr=1e-6, verbose=0)
        ]

        model.fit(
            X_fold_train, y_fold_train_oh,
            batch_size=BATCH_SIZE, epochs=EPOCHS,
            validation_data=(X_fold_val, y_fold_val_oh),
            callbacks=cb, verbose=0
        )

        _, val_acc = model.evaluate(X_fold_val, y_fold_val_oh, verbose=0)
        fold_accs.append(val_acc)
        print(f"  Fold {fold}/{KFOLDS}  验证准确率: {val_acc*100:.2f}%")

    mean_acc = np.mean(fold_accs)
    std_acc = np.std(fold_accs)
    print(f"\n  各折准确率: {[f'{a*100:.2f}%' for a in fold_accs]}")
    print(f"  平均准确率: {mean_acc*100:.2f}% ± {std_acc*100:.2f}%")

    return fold_accs, mean_acc, std_acc


def plot_training_history(history, model_name):
    """绘制训练曲线"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    ax1.plot(history["loss"], label="Train Loss")
    ax1.plot(history["val_loss"], label="Val Loss")
    ax1.set_title(f"{model_name} - Loss")
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("Loss")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.plot(history["accuracy"], label="Train Acc")
    ax2.plot(history["val_accuracy"], label="Val Acc")
    ax2.set_title(f"{model_name} - Accuracy")
    ax2.set_xlabel("Epoch")
    ax2.set_ylabel("Accuracy")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(MODELS_DIR, f"{model_name}_training_curve.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  训练曲线: {model_name}_training_curve.png")


def print_confusion_matrix(y_true, y_pred, classes):
    """打印混淆矩阵"""
    cm = confusion_matrix(y_true, y_pred)
    print("\n混淆矩阵 (行=真实标签, 列=预测标签):")
    header = "           " + "".join(f"{c[:6]:>8}" for c in classes)
    print(header)
    for i, cls in enumerate(classes):
        row = f"  {cls[:6]:>8}" + "".join(f"{cm[i][j]:>8}" for j in range(len(classes)))
        print(row)
    return cm


def train_model(model_type, X_train, y_train, X_test, y_test, classes):
    """训练单个模型：5折交叉验证 + 全量训练 + 测试评估"""
    num_classes = len(classes)
    input_shape = X_train.shape[1:]

    print("\n" + "=" * 60)
    print(f"训练模型: {model_type.upper()}")
    print("=" * 60)
    print(f"  输入形状: {input_shape}  类别数: {num_classes}")

    # ---------- 5 折交叉验证 ----------
    fold_accs, cv_mean, cv_std = run_cross_validation(
        X_train, y_train, model_type, num_classes, classes
    )

    # ---------- 全量训练最终模型 ----------
    print(f"\n{'='*60}")
    print(f"  训练最终 {model_type.upper()} 模型（全部训练数据）")
    print(f"{'='*60}")

    y_train_oh = tf.keras.utils.to_categorical(y_train, num_classes)
    y_test_oh = tf.keras.utils.to_categorical(y_test, num_classes)

    model = build_model(model_type, input_shape, num_classes)
    model.summary()
    model.compile(
        optimizer=optimizers.Adam(learning_rate=LEARNING_RATE),
        loss="categorical_crossentropy",
        metrics=["accuracy"]
    )

    cb = [
        callbacks.EarlyStopping("val_accuracy", patience=PATIENCE,
                                restore_best_weights=True, verbose=1),
        callbacks.ReduceLROnPlateau("val_loss", factor=0.5, patience=7,
                                    min_lr=1e-6, verbose=1),
        callbacks.ModelCheckpoint(
            os.path.join(MODELS_DIR, f"{model_type}_best.h5"),
            monitor="val_accuracy", save_best_only=True, verbose=1
        )
    ]

    # 全量训练，切 10% 作为验证集
    history = model.fit(
        X_train, y_train_oh,
        batch_size=BATCH_SIZE, epochs=EPOCHS,
        validation_split=0.1,
        callbacks=cb, verbose=1
    )

    plot_training_history(history.history, model_type)

    # ---------- 测试集评估 ----------
    print(f"\n{'='*60}")
    print(f"  {model_type.upper()} 测试集评估")
    print(f"{'='*60}")

    test_loss, test_acc = model.evaluate(X_test, y_test_oh, verbose=0)
    y_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)

    print(f"\n测试准确率: {test_acc*100:.2f}%")
    print_confusion_matrix(y_test, y_pred, classes)

    print(f"\n分类报告:")
    print(classification_report(y_test, y_pred, target_names=classes, digits=3))

    # ---------- 保存 ----------
    model.save(os.path.join(MODELS_DIR, f"{model_type}_final.h5"))
    print(f"\n  模型已保存: {model_type}_final.h5")

    # TFLite 导出
    print("  正在导出 TFLite 模型...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    tflite_path = os.path.join(MODELS_DIR, f"{model_type}.tflite")
    with open(tflite_path, "wb") as f:
        f.write(tflite_model)
    print(f"  TFLite 模型已保存: {tflite_path}")

    return {
        "cv_fold_accs": [float(a) for a in fold_accs],
        "cv_mean": float(cv_mean),
        "cv_std": float(cv_std),
        "test_acc": float(test_acc),
        "test_loss": float(test_loss),
    }


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)

    X_train, X_test, y_train, y_test, classes = load_data()

    results = {}

    # 训练 CNN-LSTM
    results["cnn_lstm"] = train_model(
        "cnn_lstm", X_train, y_train, X_test, y_test, classes
    )

    # 训练 Transformer
    results["transformer"] = train_model(
        "transformer", X_train, y_train, X_test, y_test, classes
    )

    # 汇总结果
    print("\n" + "=" * 60)
    print("训练完成！结果汇总")
    print("=" * 60)
    for name, res in results.items():
        print(f"\n  {name.upper()}:")
        print(f"    交叉验证: {res['cv_mean']*100:.2f}% ± {res['cv_std']*100:.2f}%")
        print(f"    各折: {[f'{a*100:.1f}%' for a in res['cv_fold_accs']]}")
        print(f"    测试集:   {res['test_acc']*100:.2f}%")

    best = "cnn_lstm" if results["cnn_lstm"]["test_acc"] >= results["transformer"]["test_acc"] else "transformer"
    print(f"\n  最佳模型: {best}")

    summary = {
        "data_split": f"8:2 (train={len(X_train)}, test={len(X_test)})",
        "kfolds": KFOLDS,
        "cnn_lstm": {
            "cv_mean": f"{results['cnn_lstm']['cv_mean']*100:.2f}%",
            "cv_std": f"{results['cnn_lstm']['cv_std']*100:.2f}%",
            "cv_folds": [f"{a*100:.2f}%" for a in results['cnn_lstm']['cv_fold_accs']],
            "test_acc": f"{results['cnn_lstm']['test_acc']*100:.2f}%",
        },
        "transformer": {
            "cv_mean": f"{results['transformer']['cv_mean']*100:.2f}%",
            "cv_std": f"{results['transformer']['cv_std']*100:.2f}%",
            "cv_folds": [f"{a*100:.2f}%" for a in results['transformer']['cv_fold_accs']],
            "test_acc": f"{results['transformer']['test_acc']*100:.2f}%",
        },
        "best_model": best,
    }
    with open(os.path.join(MODELS_DIR, "training_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()