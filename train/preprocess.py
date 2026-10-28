# -*- coding: utf-8 -*-
"""
语音数据预处理模块
功能：加载 wav 文件 → 重采样 16kHz → 标准化 → 提取 MFCC 特征 → 数据划分
"""
import os
import json
import numpy as np
import librosa
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import pickle

# ============ 配置参数 ============
SAMPLE_RATE = 16000          # 统一采样率 16kHz
N_MFCC = 40                  # MFCC 特征维度
N_TIME_STEPS = 128           # 时间步（通过 padding/截断统一）
DATA_DIR = os.path.join("data", "data2")
TRAIN_DIR = os.path.join(DATA_DIR, "train")
TEST_DIR = os.path.join(DATA_DIR, "test")
OUTPUT_DIR = "processed_data"

# 7 类婴儿情绪标签（中文映射）
LABEL_CN = {
    "hug": "要抱抱",
    "hungry": "饿了",
    "sleepy": "困了",
    "awake": "醒了",
    "diaper": "换尿布",
    "uncomfortable": "不舒服",
    "silence": "安静"
}


def extract_mfcc(file_path, sr=SAMPLE_RATE, n_mfcc=N_MFCC, n_time=N_TIME_STEPS):
    """
    提取 MFCC 特征并统一时间维度
    步骤：加载 → 重采样 16kHz → 标准化 → 提取 MFCC → Padding/截断
    """
    try:
        audio, orig_sr = librosa.load(file_path, sr=sr)
    except Exception as e:
        print(f"  警告：无法加载 {file_path}: {e}")
        return None

    # 标准化：均值 0，方差 1
    if np.std(audio) > 1e-6:
        audio = (audio - np.mean(audio)) / np.std(audio)
    else:
        audio = audio - np.mean(audio)

    # 提取 MFCC
    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=n_mfcc)

    # 统一时间维度
    if mfcc.shape[1] < n_time:
        pad_width = n_time - mfcc.shape[1]
        mfcc = np.pad(mfcc, ((0, 0), (0, pad_width)), mode="constant")
    else:
        mfcc = mfcc[:, :n_time]

    return mfcc  # shape: (n_mfcc, n_time)


def load_dataset(train_dir):
    """
    加载数据集，只加载同时拥有 .wav 和 .json 的标注样本
    """
    features, labels, filenames = [], [], []
    wav_files = [f for f in os.listdir(train_dir) if f.endswith(".wav")]

    loaded, skipped = 0, 0
    for wav_file in sorted(wav_files):
        base = wav_file[:-4]
        json_file = base + ".json"
        json_path = os.path.join(train_dir, json_file)
        wav_path = os.path.join(train_dir, wav_file)

        if not os.path.exists(json_path):
            skipped += 1
            continue

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        label = data["labels"][0]["name"]

        mfcc = extract_mfcc(wav_path)
        if mfcc is None:
            skipped += 1
            continue

        features.append(mfcc)
        labels.append(label)
        filenames.append(wav_file)
        loaded += 1

    print(f"  加载完成：成功 {loaded} 个，跳过 {skipped} 个")
    return np.array(features), np.array(labels), np.array(filenames)


def preprocess_all():
    """完整预处理流程"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("步骤 1：加载数据集")
    print("=" * 60)
    X, y_raw, fnames = load_dataset(TRAIN_DIR)

    # 标签编码
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y_raw)

    print(f"\n特征矩阵形状: {X.shape}")  # (N, 40, 128)
    print(f"标签分布: {dict(zip(label_encoder.classes_, np.bincount(y)))}")
    print(f"类别映射: {dict(enumerate(label_encoder.classes_))}")

    # 添加通道维度 (N, 40, 128, 1) → CNN 需要
    X = X[..., np.newaxis]

    # 划分训练/验证/测试集 (70/15/15)
    print("\n" + "=" * 60)
    print("步骤 2：数据划分 (70% 训练 / 15% 验证 / 15% 测试)")
    print("=" * 60)
    X_train, X_temp, y_train, y_temp, fn_train, fn_temp = train_test_split(
        X, y, fnames, test_size=0.3, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test, fn_val, fn_test = train_test_split(
        X_temp, y_temp, fn_temp, test_size=0.5, random_state=42, stratify=y_temp
    )

    print(f"  训练集: {len(X_train)} 样本")
    print(f"  验证集: {len(X_val)} 样本")
    print(f"  测试集: {len(X_test)} 样本")

    # 保存预处理数据
    print("\n" + "=" * 60)
    print("步骤 3：保存预处理数据")
    print("=" * 60)

    np.savez(os.path.join(OUTPUT_DIR, "dataset.npz"),
             X_train=X_train, X_val=X_val, X_test=X_test,
             y_train=y_train, y_val=y_val, y_test=y_test,
             fn_train=fn_train, fn_val=fn_val, fn_test=fn_test)

    # 保存标签编码器
    with open(os.path.join(OUTPUT_DIR, "label_encoder.pkl"), "wb") as f:
        pickle.dump(label_encoder, f)

    # 保存标签映射配置（供微信小程序使用）
    label_config = {
        "classes": label_encoder.classes_.tolist(),
        "mapping": LABEL_CN,
        "class_to_id": {cls: int(i) for i, cls in enumerate(label_encoder.classes_)},
        "id_to_class": {int(i): cls for i, cls in enumerate(label_encoder.classes_)},
    }
    with open(os.path.join(OUTPUT_DIR, "label_config.json"), "w", encoding="utf-8") as f:
        json.dump(label_config, f, ensure_ascii=False, indent=2)

    print("  已保存:")
    print(f"    {os.path.join(OUTPUT_DIR, 'dataset.npz')}")
    print(f"    {os.path.join(OUTPUT_DIR, 'label_encoder.pkl')}")
    print(f"    {os.path.join(OUTPUT_DIR, 'label_config.json')}")
    print("\n预处理完成！")


if __name__ == "__main__":
    preprocess_all()