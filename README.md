# 婴儿哭声情感分类系统

基于深度学习的婴儿哭声情感识别项目，支持 **CNN-LSTM** 与 **Transformer** 两种模型，识别 7 类婴儿情绪，并提供 Flask API 与微信小程序前端。

---

## 实验流程总览

```
① 环境准备 → ② 数据预处理 → ③ 模型训练 → ④ 模型评估 → ⑤ 推理服务 → ⑥ 小程序对接
```

| 阶段 | 脚本 | 输入 | 输出 |
|------|------|------|------|
| ① 环境准备 | `install_deps.py` | - | Python 依赖 |
| ② 数据预处理 | `preprocess.py` | `data/data2/train/*.wav + .json` | `processed_data/dataset.npz` |
| ③ 模型训练 | `train.py` | `processed_data/dataset.npz` | `models_output/*.h5` |
| ④ 模型评估 | `eval_cv_short.py` / `eval_per_class.py` / `visualize_results.py` | 训练好的模型 | 准确率、混淆矩阵、可视化图表 |
| ⑤ 推理服务 | `predict.py` / `app.py` | 模型 + 音频文件 | 预测结果 / Flask API |
| ⑥ 小程序对接 | `miniprogram/` | Flask API 地址 | 微信小程序界面 |

---

## ① 环境准备

### 依赖环境
- Python 3.7+
- TensorFlow 2.11.0（CPU 版即可）
- Librosa 0.10.2、NumPy 1.21.6、Scikit-learn 1.0.2
- Flask 2.0+、flask-cors、Matplotlib 3.5+

### 安装命令
```bash
python install_deps.py
# 或手动安装
pip install tensorflow-cpu==2.11.0 librosa==0.10.2 numpy==1.21.6 scikit-learn==1.0.2 flask flask-cors matplotlib
```

---

## ② 数据预处理

**脚本**: `preprocess.py`
**数据目录**: `data/data2/train/`（WAV + 同名 JSON 标注）

### 7 类情绪标签

| 英文 | 中文 | 英文 | 中文 |
|------|------|------|------|
| hug | 要抱抱 | diaper | 换尿布 |
| hungry | 饿了 | uncomfortable | 不舒服 |
| sleepy | 困了 | silence | 安静 |
| awake | 醒了 | | |

### 预处理流水线
```
原始 WAV
  ↓ librosa.load(sr=16000)        重采样至 16kHz
  ↓ 标准化 (均值=0, 方差=1)        消除音量差异
  ↓ librosa.feature.mfcc(n_mfcc=40) 提取 MFCC 特征
  ↓ Padding/截断至 128 帧          统一时间维度
  ↓ 添加通道维度 → (40, 128, 1)    适配 CNN 输入
```

### 运行
```bash
python preprocess.py
```

### 输出文件
```
processed_data/
├── dataset.npz          # 特征数据 (X_train/X_val/X_test, y_train/...)
├── label_config.json    # 标签映射配置（小程序也用）
└── label_encoder.pkl    # sklearn 标签编码器
```

### 关键参数
| 参数 | 值 | 说明 |
|-----|-----|------|
| `SAMPLE_RATE` | 16000 Hz | 统一采样率 |
| `N_MFCC` | 40 | MFCC 特征维度 |
| `N_TIME_STEPS` | 128 | 统一时间帧数 |
| 预处理划分 | 70/15/15 | 预处理阶段缓存（训练时合并后重新 8:2 划分） |

---

## ③ 模型训练

**脚本**: `train.py`

### 模型架构

**CNN-LSTM**（[models.py](file:///d:/Code/Voice/baby_voice/models.py)）
```
输入 (40, 128, 1)
  ├─ Conv2D(32) + BN + MaxPool + Dropout(0.3)
  ├─ Conv2D(64) + BN + MaxPool + Dropout(0.3)
  ├─ Conv2D(128) + BN + MaxPool(2,1) + Dropout(0.3)
  ├─ Reshape → (time, features)
  ├─ LSTM(128, return_sequences=True) + Dropout(0.3)
  ├─ LSTM(64) + Dropout(0.3)
  ├─ Dense(128) + Dropout(0.5)
  ├─ Dense(64) + Dropout(0.5)
  └─ Dense(7, softmax)
```

**Transformer**（[models.py](file:///d:/Code/Voice/baby_voice/models.py)）
```
输入 (40, 128, 1)
  ├─ Conv2D(32) + BN + MaxPool + Dropout(0.2)
  ├─ Conv2D(64) + BN + MaxPool + Dropout(0.2)
  ├─ Reshape → Dense(64)
  ├─ PositionalEncoding(64)
  ├─ TransformerEncoder × 3  (4 heads, ff_dim=256)
  ├─ GlobalAveragePooling1D
  ├─ Dense(128) + Dropout(0.5)
  └─ Dense(7, softmax)
```

### 训练流程
1. **重新划分**: 合并预处理数据后按 **8:2** 切分训练/测试集
2. **5 折交叉验证** (StratifiedKFold): 评估模型稳定性，输出各折准确率与均值±方差
3. **全量训练最终模型**: 使用全部训练数据 + EarlyStopping + ReduceLROnPlateau
4. **测试集评估**: 计算准确率、混淆矩阵、分类报告
5. **模型导出**: 保存 `.h5` + 转换 `.tflite`

### 运行
```bash
python train.py
```

### 训练配置
| 参数 | 值 |
|-----|-----|
| 优化器 | Adam |
| 学习率 | 0.001 |
| 损失函数 | categorical_crossentropy |
| batch_size | 32 |
| epochs | 80 |
| EarlyStopping patience | 15 |
| 学习率衰减 | factor=0.5, patience=7 |

### 输出文件
```
models_output/
├── cnn_lstm_best.h5         # CNN-LSTM 最佳权重
├── cnn_lstm_final.h5        # CNN-LSTM 最终模型
├── cnn_lstm.tflite          # CNN-LSTM TFLite
├── transformer_best.h5      # Transformer 最佳权重
├── transformer_final.h5     # Transformer 最终模型
├── transformer.tflite       # Transformer TFLite
├── {model}_training_curve.png  # 训练曲线图
└── training_summary.json    # 训练结果摘要
```

---

## ④ 模型评估

> 所有评估脚本统一采用 **8:2 数据划分**（合并预处理数据后 `train_test_split`, stratify, random_state=42），与训练阶段一致。

### 4.1 快速评估（混淆矩阵 + 分类报告）
```bash
python eval_cv_short.py
```
按 8:2 划分测试集，输出每个模型的测试准确率、混淆矩阵（文本）、sklearn 分类报告。

### 4.2 按类别详细评估
```bash
python eval_per_class.py
```
输出每个类别的样本数、正确数、准确率，以及完整 precision/recall/f1。

### 4.4 综合评估可视化（推荐）
```bash
python visualize_results.py
```
一次性生成全部评估图表，输出至 `plots/` 目录：

| 图表文件 | 内容 |
|---------|------|
| `{model}_confusion_matrix.png` | 原始混淆矩阵热图 |
| `{model}_confusion_matrix_norm.png` | 归一化混淆矩阵（按行，百分比） |
| `accuracy_comparison.png` | 两模型整体准确率对比柱状图 |
| `class_accuracy_comparison.png` | 各类别准确率对比柱状图 |
| `class_metrics_comparison.png` | 精确率/召回率/F1 三图对比 |
| `evaluation_data.json` | 评估数据（准确率、混淆矩阵） |

### 当前评估结果（8:2 划分）

| 模型 | 测试准确率 | 随机基准(7类) |
|------|-----------|--------------|
| CNN-LSTM | 32.76% | 14.3% |
| Transformer | 35.63% | 14.3% |

> 两个模型均显著超过随机基准；受限于数据量（约 866 条，训练集 692 条），可通过数据增强进一步提升。

---

## ⑤ 推理服务

### 5.1 命令行单次预测
```bash
python predict.py path/to/audio.wav
```
输出预测情绪、置信度、各类别概率。

### 5.2 启动 Flask API 服务
```bash
python app.py
# 默认启动在 http://0.0.0.0:5000
```

### API 接口列表

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/info` | GET | 获取模型和标签信息 |
| `/api/predict` | POST | 上传音频文件预测（multipart/form-data） |
| `/api/predict/base64` | POST | Base64 音频数据预测 |
| `/api/convert/formats` | GET | 支持的音频转换格式 |
| `/api/convert` | POST | 音频格式转换 |
| `/api/secrets` | POST | 设置外部 API 密钥 |
| `/api/secrets/<key>` | DELETE | 删除 API 密钥 |

### 预测请求示例
```bash
curl -X POST http://localhost:5000/api/predict \
  -F "audio=@baby_cry.wav" \
  -F "model=cnn_lstm" \
  -F "source=local"
```

### 响应格式
```json
{
  "emotion": "hug",
  "emo_cn": "要抱抱",
  "confidence": 0.85,
  "probabilities": [
    {"class": "hug", "cn": "要抱抱", "probability": 0.85},
    {"class": "hungry", "cn": "饿了", "probability": 0.08}
  ],
  "model_used": "cnn_lstm"
}
```

---

## ⑥ 微信小程序对接

**目录**: `miniprogram/`

### 功能模块
- **index 页**: 录音 → 上传 Flask API → 展示预测结果，支持模型切换（CNN-LSTM / Transformer / 外部 API）
- **history 页**: 本地存储识别历史，支持查看和删除
- **settings 页**: 配置后端服务地址、管理 API 密钥（加密存储）

### 配置后端地址
在小程序设置页填入 Flask 服务地址（开发时用局域网 IP）：
```
http://192.168.x.x:5000
```

### 标签一致性
小程序 `app.js` 中的 `globalData.labels` 必须与后端 `label_config.json` 保持一致。

---

## 项目结构

```
baby_voice/
├── preprocess.py              # ② 数据预处理
├── models.py                  # ③ 模型定义（CNN-LSTM / Transformer）
├── train.py                   # ③ 主训练脚本（5 折 CV + 全量训练）
├── train_cv.py                # ③ 训练脚本变体
├── train_cnn_lstm.py          # ③ CNN-LSTM 单独训练
├── train_transformer.py       # ③ Transformer 单独训练
├── eval_cv_short.py           # ④ 快速评估（8:2 划分）
├── eval_per_class.py          # ④ 按类别评估
├── visualize_results.py       # ④ 综合评估可视化（8:2 划分，推荐）
├── predict.py                 # ⑤ 推理模块 + Flask API
├── app.py                     # ⑤ Flask API 服务入口
├── install_deps.py            # ① 依赖安装
│
├── controllers/               # ⑤ Flask 控制器
├── services/                  # ⑤ 业务服务层
├── utils/                     # ⑤ 工具模块（音频处理等）
│
├── processed_data/            # ② 预处理输出
├── models_output/             # ③ 训练输出
├── plots/                     # ④ 评估图表
├── data/data2/                # ① 原始数据集
│
├── miniprogram/               # ⑥ 微信小程序
│   ├── pages/{index,history,settings}/
│   └── utils/{api,storage,crypto}.js
│
├── paper/                     # 参考论文
└── 总结/                       # 大纲与汇报材料
```

---

## 完整流程一键运行

```bash
# 1. 安装依赖
python install_deps.py

# 2. 数据预处理
python preprocess.py

# 3. 模型训练（CNN-LSTM + Transformer）
python train.py

# 4. 模型评估
python eval_cv_short.py
python eval_per_class.py
python visualize_results.py

# 5. 启动推理 API
python app.py

# 6. 单文件预测测试
python predict.py XIANG/想抱抱.wav
```

---

## 参考文献

1. 才让卓玛, 刘鹏飞, 马光祥. 婴儿情感识别综述[J]. 计算机工程与应用, 2024, 60(19):32-45.
2. 刘延昊. 基于卷积循环神经网络的婴儿哭声情感识别研究与应用[D]. 济南大学, 2024.
3. 王之禹, 雷云珊. 婴儿啼哭声的声学特征[C]. 中国声学学会 2006 年全国声学学术会议论文集.
4. 王晰墨. 基于深度学习的婴儿啼哭情感分析研究.
5. 余莉萍. 基于改进 LSTM 的儿童语音情感识别模型.
