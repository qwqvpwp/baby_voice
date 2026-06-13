# 婴儿哭声情感分类 - 模型说明文档

## 项目概述

本项目实现了一个基于深度学习的婴儿哭声情感分类系统，支持 CNN-LSTM 和 Transformer 两种模型架构。通过分析婴儿哭声的音频特征，自动识别婴儿的 7 种情绪状态，为家长提供育儿辅助建议。

**7 类情绪标签（中英文对照）：**

| 英文标签 | 中文含义 | 图标 |
|---------|---------|------|
| awake | 醒了 | 👀 |
| diaper | 换尿布 | 🧷 |
| hug | 要抱抱 | 🤗 |
| hungry | 饿了 | 🍼 |
| silence | 安静 | 😊 |
| sleepy | 困了 | 😴 |
| uncomfortable | 不舒服 | 😣 |

> **重要：** 以上标签需与微信小程序前端 `app.js` 中的 `globalData.labels` 保持一致。

---

## 数据预处理流程

按照《3-语音分类.pdf》指导书的预处理方法：

### 1. 数据加载
- 数据集格式：WAV 音频 + JSON 标签
- 采样率统一为 **16kHz**（与指导书一致）
- JSON 标签格式：`{"labels": [{"name": "hug"}]}`

### 2. 预处理步骤
```
原始 WAV → librosa.load(sr=16000) → 标准化(均值0,方差1) → MFCC 提取 → Padding/截断(128帧)
```

### 3. 特征参数
| 参数 | 值 | 说明 |
|-----|-----|------|
| SAMPLE_RATE | 16000 Hz | 统一采样率 |
| N_MFCC | 40 | MFCC 特征维度 |
| N_TIME_STEPS | 128 | 统一时间帧数 |
| 标准化 | 均值=0, 方差=1 | 消除音量差异 |

### 4. 数据集划分
- 训练集：70% (606 样本)
- 验证集：15% (130 样本)
- 测试集：15% (130 样本)
- 使用 `stratify=y` 保证类别分布均衡

### 5. 预处理输出文件
```
processed_data/
├── dataset.npz          # 预处理后的特征数据
├── label_config.json    # 标签映射配置
└── label_encoder.pkl    # sklearn 标签编码器
```

---

## 模型架构设计

### 模型一：CNN-LSTM 混合模型

**设计原理：** CNN 提取局部频谱特征，LSTM 捕捉时序依赖关系。

```
输入 (40, 128, 1)
  │
  ├─ Conv2D(32, 3x3) + BN + MaxPool(2x2) + Dropout(0.3)
  ├─ Conv2D(64, 3x3) + BN + MaxPool(2x2) + Dropout(0.3)
  ├─ Conv2D(128, 3x3) + BN + MaxPool(2x1) + Dropout(0.3)
  ├─ Reshape → (time, features)
  ├─ LSTM(128, return_sequences=True) + Dropout(0.3)
  ├─ LSTM(64) + Dropout(0.3)
  ├─ Dense(128, ReLU) + Dropout(0.5)
  ├─ Dense(64, ReLU) + Dropout(0.5)
  └─ Dense(7, Softmax)
```

**关键参数：**
- 使用 L2 正则化（1e-4）防止过拟合
- BatchNormalization 加速收敛
- Dropout(0.3-0.5) 增强泛化能力

### 模型二：Transformer 模型

**设计原理：** 利用自注意力机制捕捉全局特征依赖。

```
输入 (40, 128, 1)
  │
  ├─ Conv2D(32, 3x3) + BN + MaxPool(2x2) + Dropout(0.2)
  ├─ Conv2D(64, 3x3) + BN + MaxPool(2x2) + Dropout(0.2)
  ├─ Reshape → (time, 64) → Dense(64)
  ├─ PositionalEncoding(64)
  ├─ TransformerEncoder × 3
  │    ├─ MultiHeadAttention(4 heads)
  │    ├─ LayerNormalization
  │    ├─ Dense(256, ReLU) → Dense(64)
  │    └─ LayerNormalization
  ├─ GlobalAveragePooling1D
  ├─ Dense(128, ReLU) + Dropout(0.5)
  └─ Dense(7, Softmax)
```

**关键参数：**
- d_model = 64, num_heads = 4, num_blocks = 3
- FF dim = 256, Dropout = 0.3

---

## 训练配置

| 参数 | CNN-LSTM | Transformer |
|-----|----------|-------------|
| 优化器 | Adam | Adam |
| 学习率 | 0.001 | 0.001 |
| 损失函数 | CategoricalCrossentropy | CategoricalCrossentropy |
| 批次大小 | 32 | 32 |
| 最大轮次 | 80 | 80 |
| Early Stopping | patience=15 | patience=15 |
| 学习率衰减 | factor=0.5, patience=7 | factor=0.5, patience=7 |

---

## 模型输出文件

```
models_output/
├── cnn_lstm_final.h5        # CNN-LSTM 最终模型 (HDF5)
├── cnn_lstm_best.h5         # CNN-LSTM 最佳模型 (验证准确率最高)
├── transformer_final.h5     # Transformer 最终模型 (HDF5)
├── transformer_best.h5      # Transformer 最佳模型 (验证准确率最高)
└── training_summary.json    # 训练结果摘要
```

---

## 使用方法

### 1. 命令行测试
```bash
# 使用 Python 解释器
python predict.py path/to/audio.wav
```

### 2. Flask API 接口

启动服务：
```bash
python app.py
```

API 接口列表：

| 路径 | 方法 | 说明 |
|------|------|------|
| /api/health | GET | 健康检查 |
| /api/info | GET | 获取模型和标签信息 |
| /api/predict | POST | 上传音频文件进行预测 |
| /api/predict/base64 | POST | Base64 音频数据预测 |
| /api/secrets | POST | 设置 API 密钥 |
| /api/secrets/<key> | DELETE | 删除 API 密钥 |

### 3. 预测请求格式

**POST /api/predict** (multipart/form-data)

| 参数 | 说明 | 示例 |
|-----|------|------|
| audio | 音频文件 | baby_cry.wav |
| model | 模型名称 | cnn_lstm / transformer |
| source | 识别来源 | local / api |

**响应格式：**
```json
{
  "emotion": "hug",
  "emo_cn": "要抱抱",
  "confidence": 0.85,
  "probabilities": [
    {"class": "hug", "cn": "要抱抱", "probability": 0.85},
    {"class": "hungry", "cn": "饿了", "probability": 0.08},
    {"class": "sleepy", "cn": "困了", "probability": 0.04},
    ...
  ],
  "model_used": "cnn_lstm"
}
```

---

## 训练结果

| 模型 | 测试准确率 | 最佳验证准确率 | 文件 |
|------|-----------|-------------|------|
| CNN-LSTM | 36.15% | - | cnn_lstm_final.h5 |
| Transformer | 39.23% | 44.62% (Epoch 27) | transformer_final.h5 |

> **随机基准（7分类）：** 14.3%
> 
> 两个模型均显著超过随机基准。Transformer 略优于 CNN-LSTM。
> 受限于训练数据量（606条），可通过数据增强进一步提升。

---

## 微信小程序对接

### 标签对应关系
小程序 `app.js` 中的 `globalData.labels` 必须与此保持一致：
```javascript
labels: {
  "awake": "醒了",
  "diaper": "换尿布",
  "hug": "要抱抱",
  "hungry": "饿了",
  "silence": "安静",
  "sleepy": "困了",
  "uncomfortable": "不舒服"
}
```

### 小程序功能模块
1. **录音识别** - 调用麦克风录音 → 上传至 Flask API → 展示结果
2. **模型切换** - 支持 CNN-LSTM / Transformer / 外部API 切换
3. **历史记录** - 本地存储识别历史，支持查看和删除
4. **API密钥管理** - 支持外部API密钥的加密本地存储

### 后端地址配置
在小程序设置页配置 Flask 服务地址（开发时用局域网IP）：
```
http://192.168.x.x:5000
```

---

## 项目文件结构

```
baby_voice/
├── preprocess.py            # 数据预处理
├── models.py                # 模型定义（类库）
├── train_cnn_lstm.py       # CNN-LSTM 训练脚本
├── train_transformer.py    # Transformer 训练脚本
├── predict.py               # 推理模块
├── app.py                   # Flask API 服务
├── processed_data/          # 预处理数据
├── models_output/           # 训练好的模型
├── data/data2/              # 原始数据集
└── miniprogram/             # 微信小程序
    ├── app.js / app.json / app.wxss
    ├── pages/
    │   ├── index/           # 录音识别页
    │   ├── history/         # 历史记录页
    │   └── settings/        # 设置页
    └── utils/
        ├── api.js           # API 通信
        ├── storage.js       # 本地存储
        └── crypto.js        # 密钥加密
```

---

## 依赖环境

- Python 3.7+ (TensorFlow-CPU 环境)
- TensorFlow 2.11.0
- Librosa 0.10.2
- NumPy 1.21.6
- Scikit-learn 1.0.2
- Flask 2.0+
- Matplotlib 3.5+