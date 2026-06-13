# -*- coding: utf-8 -*-
"""
支持 8:2 划分 + K-fold 交叉验证的训练脚本
输出混淆矩阵和详细分类报告
"""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import numpy as np
import json
import tensorflow as tf
from tensorflow.keras import layers, Model, regularizers, callbacks, optimizers
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import confusion_matrix, classification_report
import pickle

# ============ 配置参数 ============
PROCESSED_DIR = "processed_data"
MODELS_DIR = "models_output"
BATCH_SIZE = 32
EPOCHS = 80
LEARNING_RATE = 0.001
PATIENCE = 15
KFOLDS = 5              # 交叉验证折数
TEST_SIZE = 0.2         # 测试集比例
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


def transformer_block(x, d_model, num_heads, ff_dim, dropout=0.3):
    attn = layers.MultiHeadAttention(
        num_heads=num_heads, key_dim=d_model // num_heads, dropout=dropout
    )(x, x)
    attn = layers.Dropout(dropout)(attn)
    x1 = layers.LayerNormalization(epsilon=1e-6)(x + attn)
    
    ff = layers.Dense(ff_dim, activation='relu')(x1)
    ff = layers.Dense(d_model)(ff)
    ff = layers.Dropout(dropout)(ff)
    x2 = layers.LayerNormalization(epsilon=1e-6)(x1 + ff)
    return x2


def build_cnn_lstm(input_shape, num_classes):
    """构建 CNN-LSTM 模型"""
    inp = layers.Input(input_shape)
    
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
    
    x = layers.Reshape((x.shape[1] * x.shape[2], x.shape[3]))(x)
    
    x = layers.LSTM(128, return_sequences=True, dropout=0.3)(x)
    x = layers.LSTM(64, return_sequences=False, dropout=0.3)(x)
    
    x = layers.Dense(128, activation='relu', kernel_regularizer=regularizers.l2(1e-4))(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(64, activation='relu', kernel_regularizer=regularizers.l2(1e-4))(x)
    x = layers.Dropout(0.5)(x)
    
    out = layers.Dense(num_classes, activation='softmax')(x)
    return Model(inp, out, name='CNN_LSTM')


def build_transformer(input_shape, num_classes):
    """构建 Transformer 模型"""
    D_MODEL, NUM_HEADS, NUM_BLOCKS, FF_DIM = 64, 4, 3, 256
    
    inp = layers.Input(input_shape)
    
    x = layers.Conv2D(32, (3, 3), padding='same', activation='relu')(inp)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.2)(x)
    
    x = layers.Conv2D(D_MODEL, (3, 3), padding='same', activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.2)(x)
    
    x = layers.Reshape((x.shape[1] * x.shape[2], x.shape[3]))(x)
    x = layers.Dense(D_MODEL, activation='relu')(x)
    
    x = PositionalEncoding(D_MODEL)(x)
    
    for _ in range(NUM_BLOCKS):
        x = transformer_block(x, D_MODEL, NUM_HEADS, FF_DIM, 0.3)
    
    x = layers.GlobalAveragePooling1D()(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(128, activation='relu', kernel_regularizer=regularizers.l2(1e-4))(x)
    x = layers.Dropout(0.5)(x)
    
    out = layers.Dense(num_classes, activation='softmax')(x)
    return Model(inp, out, name='Transformer')


def load_data():
    """加载预处理数据并按 8:2 划分"""
    data = np.load(os.path.join(PROCESSED_DIR, "dataset.npz"))
    
    # 从 JSON 加载标签配置
    with open(os.path.join(PROCESSED_DIR, "label_config.json"), "r", encoding="utf-8") as f:
        label_cfg = json.load(f)
    classes = label_cfg['classes']
    num_classes = len(classes)
    
    X_all = np.concatenate([data["X_train"], data["X_val"], data["X_test"]])
    y_all = np.concatenate([data["y_train"], data["y_val"], data["y_test"]])
    
    print(f"\n总样本数: {len(X_all)}")
    print(f"类别数: {num_classes}")
    print(f"类别列表: {classes}")
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


def run_cross_validation(X_train, y_train, model_builder, model_name, num_classes):
    """执行 K-fold 交叉验证"""
    skf = StratifiedKFold(n_splits=KFOLDS, shuffle=True, random_state=RANDOM_STATE)
    fold_accs = []
    fold_histories = []
    
    print(f"\n{'='*60}")
    print(f"  {model_name} - {KFOLDS}-Fold 交叉验证")
    print(f"{'='*60}")
    
    for fold, (train_idx, val_idx) in enumerate(skf.split(X_train, y_train), 1):
        print(f"\n--- Fold {fold}/{KFOLDS} ---")
        
        X_fold_train, X_fold_val = X_train[train_idx], X_train[val_idx]
        y_fold_train, y_fold_val = y_train[train_idx], y_train[val_idx]
        
        y_fold_train_oh = tf.keras.utils.to_categorical(y_fold_train, num_classes)
        y_fold_val_oh = tf.keras.utils.to_categorical(y_fold_val, num_classes)
        
        model = model_builder(X_train.shape[1:], num_classes)
        model.compile(
            optimizer=optimizers.Adam(LEARNING_RATE),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        cb = [
            callbacks.EarlyStopping('val_accuracy', patience=PATIENCE,
                                    restore_best_weights=True, verbose=0),
            callbacks.ReduceLROnPlateau('val_loss', factor=0.5, patience=7,
                                        min_lr=1e-6, verbose=0)
        ]
        
        history = model.fit(
            X_fold_train, y_fold_train_oh,
            batch_size=BATCH_SIZE, epochs=EPOCHS,
            validation_data=(X_fold_val, y_fold_val_oh),
            callbacks=cb, verbose=0
        )
        
        val_loss, val_acc = model.evaluate(X_fold_val, y_fold_val_oh, verbose=0)
        fold_accs.append(val_acc)
        fold_histories.append(history.history)
        
        print(f"  验证准确率: {val_acc*100:.2f}%")
    
    print(f"\n{'='*60}")
    print(f"  交叉验证结果汇总")
    print(f"{'='*60}")
    print(f"  各折准确率: {[f'{acc*100:.2f}%' for acc in fold_accs]}")
    print(f"  平均准确率: {np.mean(fold_accs)*100:.2f}% ± {np.std(fold_accs)*100:.2f}%")
    
    return np.mean(fold_accs)


def train_final_model(X_train, y_train, X_test, y_test, model_builder, 
                      model_name, num_classes, label_encoder):
    """训练最终模型并在测试集上评估"""
    print(f"\n{'='*60}")
    print(f"  训练最终 {model_name} 模型")
    print(f"{'='*60}")
    
    y_train_oh = tf.keras.utils.to_categorical(y_train, num_classes)
    y_test_oh = tf.keras.utils.to_categorical(y_test, num_classes)
    
    model = model_builder(X_train.shape[1:], num_classes)
    model.summary()
    
    model.compile(
        optimizer=optimizers.Adam(LEARNING_RATE),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    cb = [
        callbacks.EarlyStopping('val_loss', patience=PATIENCE,
                                restore_best_weights=True, verbose=1),
        callbacks.ReduceLROnPlateau('val_loss', factor=0.5, patience=7,
                                    min_lr=1e-6, verbose=1),
        callbacks.ModelCheckpoint(os.path.join(MODELS_DIR, f'{model_name}_cv_best.h5'),
                                  'val_loss', save_best_only=True, verbose=1)
    ]
    
    history = model.fit(
        X_train, y_train_oh,
        batch_size=BATCH_SIZE, epochs=EPOCHS,
        validation_split=0.1,  # 用10%训练数据做验证
        callbacks=cb, verbose=1
    )
    
    print(f"\n{'='*60}")
    print(f"  {model_name} 测试集评估")
    print(f"{'='*60}")
    test_loss, test_acc = model.evaluate(X_test, y_test_oh, verbose=0)
    print(f"  测试准确率: {test_acc*100:.2f}%")
    
    y_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)
    
    print_confusion_matrix(y_test, y_pred, label_encoder.classes_)
    
    print(f"\n分类报告:")
    print(classification_report(
        y_test, y_pred,
        target_names=label_encoder.classes_,
        digits=3
    ))
    
    model.save(os.path.join(MODELS_DIR, f'{model_name}_cv_final.h5'))
    print(f"\n  模型已保存: {model_name}_cv_final.h5")
    
    return test_acc


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    X_train, X_test, y_train, y_test, classes = load_data()
    num_classes = len(classes)
    
    results = {}
    
    print("\n" + "="*70)
    print("1. CNN-LSTM 模型")
    print("="*70)
    run_cross_validation(X_train, y_train, build_cnn_lstm, "CNN-LSTM", num_classes)
    acc_cnn = train_final_model(X_train, y_train, X_test, y_test, 
                               build_cnn_lstm, "CNN-LSTM", num_classes, classes)
    results["cnn_lstm"] = acc_cnn
    
    print("\n" + "="*70)
    print("2. Transformer 模型")
    print("="*70)
    run_cross_validation(X_train, y_train, build_transformer, "Transformer", num_classes)
    acc_tf = train_final_model(X_train, y_train, X_test, y_test, 
                               build_transformer, "Transformer", num_classes, classes)
    results["transformer"] = acc_tf
    
    print("\n" + "="*70)
    print("最终结果对比")
    print("="*70)
    print(f"CNN-LSTM   测试准确率: {acc_cnn*100:.2f}%")
    print(f"Transformer 测试准确率: {acc_tf*100:.2f}%")
    print(f"最佳模型: {'CNN-LSTM' if acc_cnn >= acc_tf else 'Transformer'}")
    
    with open(os.path.join(MODELS_DIR, 'cv_training_summary.json'), 'w', encoding='utf-8') as f:
        json.dump({
            "cnn_lstm_accuracy": f"{acc_cnn*100:.2f}%",
            "transformer_accuracy": f"{acc_tf*100:.2f}%",
            "best_model": "cnn_lstm" if acc_cnn >= acc_tf else "transformer",
            "test_size": TEST_SIZE,
            "kfolds": KFOLDS
        }, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()